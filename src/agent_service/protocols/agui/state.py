"""
AG-UI state management for UI synchronization.

This module provides state management functionality for synchronizing
agent state with the frontend UI in real-time.
"""
import json
import logging
from typing import Any, Optional
from datetime import datetime
from copy import deepcopy

from agent_service.protocols.agui.events import StateSyncEvent, StateUpdateEvent

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manager for AG-UI state synchronization.

    Features:
    - Full state sync
    - Incremental state updates
    - State versioning
    - Nested state updates with JSON paths
    - State history tracking
    """

    def __init__(self):
        """Initialize state manager."""
        self._state: dict[str, Any] = {}
        self._version: int = 1
        self._history: list[tuple[datetime, dict[str, Any]]] = []
        self._max_history: int = 10

    def get_state(self) -> dict[str, Any]:
        """
        Get current state.

        Returns:
            Current state dictionary
        """
        return deepcopy(self._state)

    def get_version(self) -> int:
        """
        Get current state version.

        Returns:
            Current version number
        """
        return self._version

    def set_state(self, state: dict[str, Any]) -> StateSyncEvent:
        """
        Set full state and create sync event.

        Args:
            state: New state dictionary

        Returns:
            State sync event
        """
        # Save to history
        self._add_to_history(self._state)

        # Update state
        self._state = deepcopy(state)
        self._version += 1

        logger.debug(f"State updated to version {self._version}")

        # Create sync event
        return StateSyncEvent(
            state=state,
            version=self._version
        )

    def update_state(
        self,
        updates: dict[str, Any],
        path: Optional[str] = None
    ) -> StateUpdateEvent:
        """
        Update state incrementally.

        Args:
            updates: State updates to apply
            path: Optional JSON path for nested updates (e.g., "user.settings.theme")

        Returns:
            State update event
        """
        # Save to history
        self._add_to_history(self._state)

        # Apply updates
        if path:
            self._update_nested(self._state, path, updates)
        else:
            self._state.update(updates)

        self._version += 1

        logger.debug(f"State updated to version {self._version} (path: {path})")

        # Create update event
        return StateUpdateEvent(
            updates=updates,
            path=path
        )

    def get_value(self, path: str, default: Any = None) -> Any:
        """
        Get value from state by path.

        Args:
            path: JSON path (e.g., "user.settings.theme")
            default: Default value if path doesn't exist

        Returns:
            Value at path or default
        """
        try:
            value = self._state
            for key in path.split("."):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set_value(self, path: str, value: Any) -> StateUpdateEvent:
        """
        Set value in state by path.

        Args:
            path: JSON path (e.g., "user.settings.theme")
            value: Value to set

        Returns:
            State update event
        """
        # Parse path
        keys = path.split(".")
        last_key = keys[-1]
        parent_path = ".".join(keys[:-1]) if len(keys) > 1 else None

        # Get or create parent
        if parent_path:
            parent = self.get_value(parent_path, {})
            if not isinstance(parent, dict):
                parent = {}
            parent[last_key] = value
            return self.update_state({last_key: value}, parent_path)
        else:
            return self.update_state({last_key: value})

    def delete_value(self, path: str) -> StateUpdateEvent:
        """
        Delete value from state by path.

        Args:
            path: JSON path (e.g., "user.settings.theme")

        Returns:
            State update event
        """
        # Save to history
        self._add_to_history(self._state)

        # Parse path
        keys = path.split(".")
        last_key = keys[-1]

        # Navigate to parent and delete
        value = self._state
        for key in keys[:-1]:
            if key not in value:
                return StateUpdateEvent(updates={}, path=path)
            value = value[key]

        if last_key in value:
            del value[last_key]
            self._version += 1

        logger.debug(f"Deleted state value at {path}")

        # Create update event
        return StateUpdateEvent(
            updates={last_key: None},
            path=".".join(keys[:-1]) if len(keys) > 1 else None
        )

    def merge_state(self, updates: dict[str, Any]) -> StateUpdateEvent:
        """
        Deep merge updates into state.

        Args:
            updates: Updates to merge

        Returns:
            State update event
        """
        # Save to history
        self._add_to_history(self._state)

        # Deep merge
        self._deep_merge(self._state, updates)
        self._version += 1

        logger.debug(f"Merged updates into state (version {self._version})")

        # Create update event
        return StateUpdateEvent(updates=updates)

    def reset_state(self) -> StateSyncEvent:
        """
        Reset state to empty.

        Returns:
            State sync event
        """
        # Save to history
        self._add_to_history(self._state)

        # Reset
        self._state = {}
        self._version = 1

        logger.info("State reset")

        # Create sync event
        return StateSyncEvent(state={}, version=self._version)

    def get_history(self, limit: int = 10) -> list[tuple[datetime, dict[str, Any]]]:
        """
        Get state history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of (timestamp, state) tuples
        """
        return self._history[-limit:]

    def _update_nested(
        self,
        state: dict[str, Any],
        path: str,
        updates: dict[str, Any]
    ) -> None:
        """
        Update nested state by path.

        Args:
            state: State dictionary to update
            path: JSON path
            updates: Updates to apply
        """
        keys = path.split(".")
        current = state

        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Update last level
        last_key = keys[-1]
        if last_key not in current:
            current[last_key] = {}
        current[last_key].update(updates)

    def _deep_merge(self, target: dict[str, Any], source: dict[str, Any]) -> None:
        """
        Deep merge source into target.

        Args:
            target: Target dictionary
            source: Source dictionary
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = deepcopy(value)

    def _add_to_history(self, state: dict[str, Any]) -> None:
        """
        Add state to history.

        Args:
            state: State to add
        """
        self._history.append((datetime.utcnow(), deepcopy(state)))

        # Trim history if needed
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]


class RunState:
    """
    State manager for a single agent run.

    Provides a scoped state manager for tracking state during a single run.
    """

    def __init__(self, run_id: str):
        """
        Initialize run state.

        Args:
            run_id: Run identifier
        """
        self.run_id = run_id
        self.state_manager = StateManager()
        self.started_at = datetime.utcnow()
        self.finished_at: Optional[datetime] = None
        self.status: str = "running"
        self.error: Optional[str] = None

    def finish(self, error: Optional[str] = None) -> None:
        """
        Mark run as finished.

        Args:
            error: Optional error message if run failed
        """
        self.finished_at = datetime.utcnow()
        self.status = "failed" if error else "completed"
        self.error = error

    def get_metadata(self) -> dict[str, Any]:
        """
        Get run metadata.

        Returns:
            Run metadata dictionary
        """
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "error": self.error,
            "state_version": self.state_manager.get_version()
        }


# Global state manager instance
_global_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """
    Get the global state manager instance.

    Returns:
        Global StateManager instance
    """
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = StateManager()
    return _global_state_manager
