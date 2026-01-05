"""Hook execution runner"""

import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Union

from src.hooks.config import HooksConfig, HookDefinition, HookType, ErrorAction
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HookResult:
    """Result of a hook execution"""

    hook_type: HookType
    success: bool
    command: str
    return_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None
    timed_out: bool = False

    def get_status_message(self) -> str:
        """Get a human-readable status message"""
        if self.timed_out:
            return f"フック '{self.hook_type.value}' がタイムアウトしました"
        elif self.success:
            return f"フック '{self.hook_type.value}' が正常に完了しました"
        else:
            return f"フック '{self.hook_type.value}' が失敗しました: {self.error_message or 'Unknown error'}"


class HooksRunner:
    """Runner for executing hooks"""

    def __init__(
        self,
        config: HooksConfig,
        progress_callback: Optional[Callable[[str, Optional[str]], None]] = None,
    ):
        """
        Initialize hooks runner

        Args:
            config: Hooks configuration
            progress_callback: Optional callback for progress updates (status, details)
        """
        self.config = config
        self.progress_callback = progress_callback
        self._async_threads: list[threading.Thread] = []

    def _substitute_placeholders(self, command: str, **kwargs: Any) -> str:
        """
        Substitute placeholders in command with actual values

        Args:
            command: Command template with placeholders
            **kwargs: Values to substitute

        Returns:
            Command with placeholders replaced
        """
        result = command
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                # Convert Path to string if necessary
                str_value = str(value) if isinstance(value, Path) else value
                result = result.replace(placeholder, str_value)
        return result

    def _execute_command(
        self,
        hook_type: HookType,
        hook: HookDefinition,
        command: str,
    ) -> HookResult:
        """
        Execute a single command

        Args:
            hook_type: Type of hook being executed
            hook: Hook definition
            command: Command to execute (with placeholders substituted)

        Returns:
            HookResult with execution details
        """
        logger.info(f"Executing hook '{hook_type.value}': {command}")

        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=hook.timeout_seconds,
            )

            success = process.returncode == 0

            if success:
                logger.info(f"Hook '{hook_type.value}' completed successfully")
            else:
                logger.warning(
                    f"Hook '{hook_type.value}' returned non-zero exit code: {process.returncode}"
                )
                if process.stderr:
                    logger.warning(f"stderr: {process.stderr}")

            return HookResult(
                hook_type=hook_type,
                success=success,
                command=command,
                return_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
            )

        except subprocess.TimeoutExpired:
            logger.error(
                f"Hook '{hook_type.value}' timed out after {hook.timeout_seconds} seconds"
            )
            return HookResult(
                hook_type=hook_type,
                success=False,
                command=command,
                timed_out=True,
                error_message=f"Timeout after {hook.timeout_seconds} seconds",
            )

        except Exception as e:
            logger.error(f"Hook '{hook_type.value}' failed with error: {e}")
            return HookResult(
                hook_type=hook_type,
                success=False,
                command=command,
                error_message=str(e),
            )

    def _run_async(
        self,
        hook_type: HookType,
        hook: HookDefinition,
        command: str,
    ) -> None:
        """Run hook asynchronously in a background thread"""

        def _async_execute() -> None:
            result = self._execute_command(hook_type, hook, command)
            if not result.success:
                logger.warning(
                    f"Async hook '{hook_type.value}' failed: {result.error_message}"
                )

        thread = threading.Thread(target=_async_execute, daemon=True)
        thread.start()
        self._async_threads.append(thread)
        logger.info(f"Started async hook '{hook_type.value}'")

    def run_hook(
        self,
        hook_type: HookType,
        update_progress: bool = True,
        **kwargs: Any,
    ) -> Optional[HookResult]:
        """
        Run a hook if it's enabled

        Args:
            hook_type: Type of hook to run
            update_progress: Whether to update progress note
            **kwargs: Placeholder values for the command

        Returns:
            HookResult if hook was executed, None if hook is disabled or not configured
        """
        hook = self.config.get_hook(hook_type)
        if not hook:
            return None

        # Substitute placeholders
        command = self._substitute_placeholders(hook.command, **kwargs)

        # Update progress if callback is provided and update_progress is True
        if update_progress and self.progress_callback:
            self.progress_callback(
                f"フック実行中: {hook_type.value}",
                f"コマンド: {command[:50]}..."
                if len(command) > 50
                else f"コマンド: {command}",
            )

        # Execute async or sync
        if hook.run_async:
            self._run_async(hook_type, hook, command)
            return HookResult(
                hook_type=hook_type,
                success=True,
                command=command,
                stdout="Started in background",
            )
        else:
            result = self._execute_command(hook_type, hook, command)

            # Update progress with result
            if update_progress and self.progress_callback:
                if result.success:
                    self.progress_callback(
                        f"フック完了: {hook_type.value}",
                        None,
                    )
                else:
                    self.progress_callback(
                        f"フック失敗: {hook_type.value}",
                        result.error_message,
                    )

            return result

    def should_abort(self, result: Optional[HookResult]) -> bool:
        """
        Check if processing should abort based on hook result

        Args:
            result: Result from hook execution

        Returns:
            True if processing should abort
        """
        if result is None:
            return False

        hook = self.config.get_hook(result.hook_type)
        if hook and not result.success and hook.error_action == ErrorAction.ABORT:
            return True

        return False

    def wait_for_async_hooks(self, timeout: Optional[float] = None) -> None:
        """
        Wait for all async hooks to complete

        Args:
            timeout: Maximum time to wait for each thread
        """
        for thread in self._async_threads:
            if thread.is_alive():
                thread.join(timeout=timeout)
        self._async_threads.clear()

    # Convenience methods for each hook type

    def on_file_detected(self, file_path: Path) -> Optional[HookResult]:
        """
        Run on_file_detected hook

        Args:
            file_path: Path to the detected file

        Returns:
            HookResult if executed
        """
        return self.run_hook(
            HookType.ON_FILE_DETECTED,
            update_progress=False,  # No progress note for file detection
            file_path=file_path,
        )

    def on_audio_detected(self, audio_path: Path) -> Optional[HookResult]:
        """
        Run on_audio_detected hook

        Args:
            audio_path: Path to the detected audio file

        Returns:
            HookResult if executed
        """
        return self.run_hook(
            HookType.ON_AUDIO_DETECTED,
            update_progress=True,
            audio_path=audio_path,
        )

    def on_transcription_complete(
        self,
        audio_path: Path,
        transcription_path: Path,
    ) -> Optional[HookResult]:
        """
        Run on_transcription_complete hook

        Args:
            audio_path: Path to the audio file
            transcription_path: Path to the transcription file

        Returns:
            HookResult if executed
        """
        return self.run_hook(
            HookType.ON_TRANSCRIPTION_COMPLETE,
            update_progress=True,
            audio_path=audio_path,
            transcription_path=transcription_path,
        )

    def on_summary_complete(
        self,
        audio_path: Path,
        transcription_path: Path,
        summary_path: Path,
    ) -> Optional[HookResult]:
        """
        Run on_summary_complete hook

        Args:
            audio_path: Path to the audio file
            transcription_path: Path to the transcription file
            summary_path: Path to the summary file

        Returns:
            HookResult if executed
        """
        return self.run_hook(
            HookType.ON_SUMMARY_COMPLETE,
            update_progress=False,  # Last hook, no progress note needed
            audio_path=audio_path,
            transcription_path=transcription_path,
            summary_path=summary_path,
        )
