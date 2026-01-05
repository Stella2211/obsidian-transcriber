"""Tests for hooks functionality"""

import tempfile
from pathlib import Path
import pytest

from src.hooks.config import (
    HooksConfig,
    HookDefinition,
    HookType,
    ErrorAction,
    create_default_hooks_config,
)
from src.hooks.runner import HooksRunner, HookResult


class TestHookDefinition:
    """Tests for HookDefinition class"""

    def test_from_dict_minimal(self):
        """Test creating HookDefinition from minimal dict"""
        data = {"command": "echo test"}
        hook = HookDefinition.from_dict(data)

        assert hook.command == "echo test"
        assert hook.enabled is True
        assert hook.timeout_seconds == 300
        assert hook.error_action == ErrorAction.CONTINUE
        assert hook.run_async is False

    def test_from_dict_full(self):
        """Test creating HookDefinition from full dict"""
        data = {
            "command": "echo test",
            "enabled": False,
            "timeout_seconds": 60,
            "error_action": "abort",
            "run_async": True,
        }
        hook = HookDefinition.from_dict(data)

        assert hook.command == "echo test"
        assert hook.enabled is False
        assert hook.timeout_seconds == 60
        assert hook.error_action == ErrorAction.ABORT
        assert hook.run_async is True

    def test_to_dict(self):
        """Test converting HookDefinition to dict"""
        hook = HookDefinition(
            command="echo test",
            enabled=True,
            timeout_seconds=120,
            error_action=ErrorAction.ABORT,
            run_async=False,
        )
        data = hook.to_dict()

        assert data["command"] == "echo test"
        assert data["enabled"] is True
        assert data["timeout_seconds"] == 120
        assert data["error_action"] == "abort"
        assert data["run_async"] is False


class TestHooksConfig:
    """Tests for HooksConfig class"""

    def test_default_config(self):
        """Test creating default HooksConfig"""
        config = HooksConfig()

        assert config.hooks_enabled is True
        assert config.on_file_detected is None
        assert config.on_audio_detected is None
        assert config.on_transcription_complete is None
        assert config.on_summary_complete is None

    def test_get_hook_disabled_globally(self):
        """Test get_hook returns None when hooks are disabled globally"""
        config = HooksConfig(
            hooks_enabled=False,
            on_file_detected=HookDefinition(command="echo test"),
        )

        assert config.get_hook(HookType.ON_FILE_DETECTED) is None

    def test_get_hook_disabled_individually(self):
        """Test get_hook returns None when specific hook is disabled"""
        config = HooksConfig(
            on_file_detected=HookDefinition(command="echo test", enabled=False),
        )

        assert config.get_hook(HookType.ON_FILE_DETECTED) is None

    def test_get_hook_enabled(self):
        """Test get_hook returns hook when enabled"""
        hook = HookDefinition(command="echo test", enabled=True)
        config = HooksConfig(on_file_detected=hook)

        result = config.get_hook(HookType.ON_FILE_DETECTED)
        assert result == hook

    def test_has_enabled_hooks_false(self):
        """Test has_enabled_hooks returns False when no hooks enabled"""
        config = HooksConfig()
        assert config.has_enabled_hooks() is False

    def test_has_enabled_hooks_true(self):
        """Test has_enabled_hooks returns True when hook enabled"""
        config = HooksConfig(
            on_file_detected=HookDefinition(command="echo test", enabled=True),
        )
        assert config.has_enabled_hooks() is True

    def test_from_yaml_nonexistent(self):
        """Test loading from nonexistent YAML file returns default config"""
        config = HooksConfig.from_yaml(Path("/nonexistent/path.yaml"))

        assert config.hooks_enabled is True
        assert config.on_file_detected is None

    def test_from_yaml_valid(self):
        """Test loading from valid YAML file"""
        yaml_content = """
settings:
  enabled: true

hooks:
  on_file_detected:
    command: "echo {file_path}"
    enabled: true
    timeout_seconds: 60
  on_audio_detected:
    command: "echo {audio_path}"
    enabled: false
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            config = HooksConfig.from_yaml(Path(f.name))

            assert config.hooks_enabled is True
            assert config.on_file_detected is not None
            assert config.on_file_detected.command == "echo {file_path}"
            assert config.on_file_detected.enabled is True
            assert config.on_file_detected.timeout_seconds == 60
            assert config.on_audio_detected is not None
            assert config.on_audio_detected.enabled is False

    def test_create_default_hooks_config(self):
        """Test creating default hooks config with examples"""
        config = create_default_hooks_config()

        assert config.on_file_detected is not None
        assert config.on_file_detected.enabled is False
        assert config.on_audio_detected is not None
        assert config.on_transcription_complete is not None
        assert config.on_summary_complete is not None


class TestHooksRunner:
    """Tests for HooksRunner class"""

    def test_substitute_placeholders(self):
        """Test placeholder substitution"""
        config = HooksConfig()
        runner = HooksRunner(config)

        command = "echo {file_path} {audio_path}"
        result = runner._substitute_placeholders(
            command,
            file_path="/path/to/file.mp3",
            audio_path="/path/to/audio.wav",
        )

        assert result == "echo /path/to/file.mp3 /path/to/audio.wav"

    def test_substitute_placeholders_with_path_objects(self):
        """Test placeholder substitution with Path objects"""
        config = HooksConfig()
        runner = HooksRunner(config)

        command = "echo {file_path}"
        result = runner._substitute_placeholders(
            command,
            file_path=Path("/path/to/file.mp3"),
        )

        assert result == "echo /path/to/file.mp3"

    def test_run_hook_disabled(self):
        """Test run_hook returns None for disabled hooks"""
        config = HooksConfig()
        runner = HooksRunner(config)

        result = runner.run_hook(HookType.ON_FILE_DETECTED, file_path="/test")

        assert result is None

    def test_run_hook_success(self):
        """Test run_hook executes command successfully"""
        config = HooksConfig(
            on_file_detected=HookDefinition(
                command="echo 'test'",
                enabled=True,
            ),
        )
        runner = HooksRunner(config)

        result = runner.run_hook(
            HookType.ON_FILE_DETECTED,
            update_progress=False,
            file_path="/test/file.txt",
        )

        assert result is not None
        assert result.success is True
        assert result.return_code == 0

    def test_run_hook_failure(self):
        """Test run_hook handles command failure"""
        config = HooksConfig(
            on_file_detected=HookDefinition(
                command="exit 1",
                enabled=True,
            ),
        )
        runner = HooksRunner(config)

        result = runner.run_hook(
            HookType.ON_FILE_DETECTED,
            update_progress=False,
            file_path="/test/file.txt",
        )

        assert result is not None
        assert result.success is False
        assert result.return_code == 1

    def test_run_hook_timeout(self):
        """Test run_hook handles timeout"""
        config = HooksConfig(
            on_file_detected=HookDefinition(
                command="sleep 10",
                enabled=True,
                timeout_seconds=1,
            ),
        )
        runner = HooksRunner(config)

        result = runner.run_hook(
            HookType.ON_FILE_DETECTED,
            update_progress=False,
            file_path="/test/file.txt",
        )

        assert result is not None
        assert result.success is False
        assert result.timed_out is True

    def test_should_abort_continue(self):
        """Test should_abort returns False for continue action"""
        config = HooksConfig(
            on_file_detected=HookDefinition(
                command="exit 1",
                enabled=True,
                error_action=ErrorAction.CONTINUE,
            ),
        )
        runner = HooksRunner(config)

        result = HookResult(
            hook_type=HookType.ON_FILE_DETECTED,
            success=False,
            command="exit 1",
        )

        assert runner.should_abort(result) is False

    def test_should_abort_true(self):
        """Test should_abort returns True for abort action"""
        config = HooksConfig(
            on_file_detected=HookDefinition(
                command="exit 1",
                enabled=True,
                error_action=ErrorAction.ABORT,
            ),
        )
        runner = HooksRunner(config)

        result = HookResult(
            hook_type=HookType.ON_FILE_DETECTED,
            success=False,
            command="exit 1",
        )

        assert runner.should_abort(result) is True

    def test_on_file_detected(self):
        """Test on_file_detected convenience method"""
        config = HooksConfig(
            on_file_detected=HookDefinition(
                command="echo {file_path}",
                enabled=True,
            ),
        )
        runner = HooksRunner(config)

        result = runner.on_file_detected(Path("/test/file.txt"))

        assert result is not None
        assert result.success is True

    def test_on_audio_detected(self):
        """Test on_audio_detected convenience method"""
        config = HooksConfig(
            on_audio_detected=HookDefinition(
                command="echo {audio_path}",
                enabled=True,
            ),
        )
        runner = HooksRunner(config)

        result = runner.on_audio_detected(Path("/test/audio.mp3"))

        assert result is not None
        assert result.success is True

    def test_on_transcription_complete(self):
        """Test on_transcription_complete convenience method"""
        config = HooksConfig(
            on_transcription_complete=HookDefinition(
                command="echo {audio_path} {transcription_path}",
                enabled=True,
            ),
        )
        runner = HooksRunner(config)

        result = runner.on_transcription_complete(
            Path("/test/audio.mp3"),
            Path("/test/transcription.md"),
        )

        assert result is not None
        assert result.success is True

    def test_on_summary_complete(self):
        """Test on_summary_complete convenience method"""
        config = HooksConfig(
            on_summary_complete=HookDefinition(
                command="echo {audio_path} {transcription_path} {summary_path}",
                enabled=True,
            ),
        )
        runner = HooksRunner(config)

        result = runner.on_summary_complete(
            Path("/test/audio.mp3"),
            Path("/test/transcription.md"),
            Path("/test/summary.md"),
        )

        assert result is not None
        assert result.success is True

    def test_progress_callback(self):
        """Test progress callback is called"""
        callback_calls = []

        def callback(status, details=None):
            callback_calls.append((status, details))

        config = HooksConfig(
            on_audio_detected=HookDefinition(
                command="echo test",
                enabled=True,
            ),
        )
        runner = HooksRunner(config, progress_callback=callback)

        runner.on_audio_detected(Path("/test/audio.mp3"))

        # Should have been called at least once
        assert len(callback_calls) >= 1
