"""Configuration for hooks"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, cast
import yaml

from src.utils.logging import get_logger

logger = get_logger(__name__)


class HookType(Enum):
    """Types of hooks available"""

    ON_FILE_DETECTED = "on_file_detected"
    ON_AUDIO_DETECTED = "on_audio_detected"
    ON_TRANSCRIPTION_COMPLETE = "on_transcription_complete"
    ON_SUMMARY_COMPLETE = "on_summary_complete"


class ErrorAction(Enum):
    """Action to take when a hook fails"""

    CONTINUE = "continue"  # Continue processing even if hook fails
    ABORT = "abort"  # Abort processing if hook fails


@dataclass
class HookDefinition:
    """Definition of a single hook"""

    command: str
    enabled: bool = True
    timeout_seconds: int = 300  # 5 minutes default
    error_action: ErrorAction = ErrorAction.CONTINUE
    run_async: bool = False  # Run in background

    @classmethod
    def from_dict(cls, data: dict) -> "HookDefinition":
        """Create HookDefinition from dictionary"""
        error_action = data.get("error_action", "continue")
        if isinstance(error_action, str):
            error_action = ErrorAction(error_action.lower())

        return cls(
            command=data.get("command", ""),
            enabled=data.get("enabled", True),
            timeout_seconds=data.get("timeout_seconds", 300),
            error_action=error_action,
            run_async=data.get("run_async", False),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "command": self.command,
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "error_action": self.error_action.value,
            "run_async": self.run_async,
        }


@dataclass
class HooksConfig:
    """Configuration for all hooks"""

    on_file_detected: Optional[HookDefinition] = None
    on_audio_detected: Optional[HookDefinition] = None
    on_transcription_complete: Optional[HookDefinition] = None
    on_summary_complete: Optional[HookDefinition] = None

    # Global settings
    hooks_enabled: bool = True

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "HooksConfig":
        """Load hooks configuration from YAML file"""
        if not yaml_path.exists():
            logger.info(f"Hooks config file not found: {yaml_path}")
            return cls()

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            hooks_data = data.get("hooks", {})
            global_settings = data.get("settings", {})

            config = cls(
                hooks_enabled=global_settings.get("enabled", True),
            )

            # Load each hook type
            for hook_type in HookType:
                hook_name = hook_type.value
                if hook_name in hooks_data and hooks_data[hook_name]:
                    hook_def = HookDefinition.from_dict(hooks_data[hook_name])
                    setattr(config, hook_name, hook_def)

            logger.info(f"Loaded hooks configuration from: {yaml_path}")
            return config

        except Exception as e:
            logger.error(f"Failed to load hooks config: {e}")
            return cls()

    def get_hook(self, hook_type: HookType) -> Optional[HookDefinition]:
        """Get hook definition by type"""
        if not self.hooks_enabled:
            return None

        hook: Optional[HookDefinition] = getattr(self, hook_type.value, None)
        if hook and hook.enabled:
            return hook
        return None

    def has_enabled_hooks(self) -> bool:
        """Check if any hooks are enabled"""
        if not self.hooks_enabled:
            return False

        for hook_type in HookType:
            hook = getattr(self, hook_type.value, None)
            if hook and hook.enabled:
                return True
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML export"""
        hooks = {}
        for hook_type in HookType:
            hook = getattr(self, hook_type.value, None)
            if hook:
                hooks[hook_type.value] = hook.to_dict()

        return {
            "settings": {
                "enabled": self.hooks_enabled,
            },
            "hooks": hooks,
        }

    def save_yaml(self, yaml_path: Path) -> None:
        """Save configuration to YAML file"""
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)
        logger.info(f"Saved hooks configuration to: {yaml_path}")


def create_default_hooks_config() -> HooksConfig:
    """Create a default hooks configuration with example hooks (disabled)"""
    return HooksConfig(
        on_file_detected=HookDefinition(
            command="echo 'File detected: {file_path}'",
            enabled=False,
        ),
        on_audio_detected=HookDefinition(
            command="echo 'Audio file detected: {audio_path}'",
            enabled=False,
        ),
        on_transcription_complete=HookDefinition(
            command="echo 'Transcription complete: {transcription_path}'",
            enabled=False,
        ),
        on_summary_complete=HookDefinition(
            command="echo 'Summary complete: {summary_path}'",
            enabled=False,
        ),
    )
