"""
Runtime configuration update system for the hallucination reduction feature.
Provides safe runtime updates, rollback capabilities, and change impact analysis.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from copy import deepcopy
from enum import Enum

from .config_manager import ConfigManager, ConfigChangeEvent
from .config_validator import ConfigValidator, ValidationReport
from ..models.hallucination_models import HallucinationReductionConfig


class UpdateStatus(Enum):
    """Status of a configuration update."""
    PENDING = "pending"
    VALIDATING = "validating"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ConfigUpdate:
    """Represents a configuration update request."""
    update_id: str
    timestamp: datetime
    changes: Dict[str, Any]
    requester: str
    reason: str
    status: UpdateStatus = UpdateStatus.PENDING
    validation_report: Optional[ValidationReport] = None
    error_message: Optional[str] = None
    rollback_data: Optional[Dict[str, Any]] = None


@dataclass
class UpdateResult:
    """Result of a configuration update operation."""
    success: bool
    update_id: str
    changes_applied: Dict[str, Any]
    validation_report: Optional[ValidationReport] = None
    error_message: Optional[str] = None
    rollback_available: bool = False


class RuntimeConfigUpdater:
    """
    Manages runtime configuration updates with validation, rollback, and impact analysis.
    Ensures safe configuration changes without system restart.
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.validator = ConfigValidator()
        self.logger = logging.getLogger(__name__)
        
        # Update tracking
        self.pending_updates: Dict[str, ConfigUpdate] = {}
        self.update_history: List[ConfigUpdate] = []
        self.update_counter = 0
        self._lock = threading.RLock()
        
        # Rollback support
        self.config_snapshots: Dict[str, HallucinationReductionConfig] = {}
        self.max_snapshots = 10
        
        # Update callbacks
        self.pre_update_callbacks: List[Callable[[ConfigUpdate], bool]] = []
        self.post_update_callbacks: List[Callable[[ConfigUpdate], None]] = []
        
        # Auto-rollback settings
        self.enable_auto_rollback = True
        self.rollback_timeout = timedelta(minutes=5)
        
        # Start background monitoring
        self._start_update_monitor()
    
    def request_update(self, changes: Dict[str, Any], requester: str = "system", 
                      reason: str = "Runtime update") -> str:
        """Request a configuration update."""
        with self._lock:
            self.update_counter += 1
            update_id = f"update_{self.update_counter}_{int(time.time())}"
            
            update = ConfigUpdate(
                update_id=update_id,
                timestamp=datetime.now(),
                changes=changes.copy(),
                requester=requester,
                reason=reason
            )
            
            self.pending_updates[update_id] = update
            self.logger.info(f"Configuration update requested: {update_id}")
            
            # Start async processing
            threading.Thread(target=self._process_update, args=(update_id,), daemon=True).start()
            
            return update_id
    
    def _process_update(self, update_id: str):
        """Process a configuration update asynchronously."""
        try:
            with self._lock:
                if update_id not in self.pending_updates:
                    return
                
                update = self.pending_updates[update_id]
                update.status = UpdateStatus.VALIDATING
            
            # Validate the update
            current_config = self.config_manager.get_config()
            test_config_dict = asdict(current_config)
            test_config_dict.update(update.changes)
            
            validation_report = self.validator.validate_config(test_config_dict)
            update.validation_report = validation_report
            
            if not validation_report.is_valid:
                update.status = UpdateStatus.FAILED
                update.error_message = f"Validation failed: {validation_report.summary}"
                self.logger.error(f"Update {update_id} validation failed: {validation_report.summary}")
                return
            
            # Run pre-update callbacks
            for callback in self.pre_update_callbacks:
                try:
                    if not callback(update):
                        update.status = UpdateStatus.FAILED
                        update.error_message = "Pre-update callback rejected the update"
                        self.logger.warning(f"Update {update_id} rejected by pre-update callback")
                        return
                except Exception as e:
                    self.logger.error(f"Pre-update callback error: {e}")
            
            # Create snapshot for rollback
            snapshot_id = f"snapshot_{update_id}"
            self.config_snapshots[snapshot_id] = deepcopy(current_config)
            update.rollback_data = {"snapshot_id": snapshot_id}
            
            # Apply the update
            update.status = UpdateStatus.APPLYING
            success = self.config_manager.update_config(**update.changes)
            
            if success:
                update.status = UpdateStatus.COMPLETED
                self.logger.info(f"Update {update_id} completed successfully")
                
                # Run post-update callbacks
                for callback in self.post_update_callbacks:
                    try:
                        callback(update)
                    except Exception as e:
                        self.logger.error(f"Post-update callback error: {e}")
                
                # Schedule auto-rollback check if enabled
                if self.enable_auto_rollback:
                    threading.Timer(
                        self.rollback_timeout.total_seconds(),
                        self._check_auto_rollback,
                        args=(update_id,)
                    ).start()
            else:
                update.status = UpdateStatus.FAILED
                update.error_message = "Failed to apply configuration changes"
                self.logger.error(f"Update {update_id} failed to apply")
            
        except Exception as e:
            update.status = UpdateStatus.FAILED
            update.error_message = f"Update processing error: {e}"
            self.logger.error(f"Error processing update {update_id}: {e}")
        
        finally:
            # Move to history
            with self._lock:
                if update_id in self.pending_updates:
                    self.update_history.append(self.pending_updates.pop(update_id))
                    
                    # Limit history size
                    if len(self.update_history) > 100:
                        self.update_history = self.update_history[-50:]
    
    def get_update_status(self, update_id: str) -> Optional[ConfigUpdate]:
        """Get the status of a configuration update."""
        with self._lock:
            # Check pending updates
            if update_id in self.pending_updates:
                return deepcopy(self.pending_updates[update_id])
            
            # Check history
            for update in self.update_history:
                if update.update_id == update_id:
                    return deepcopy(update)
            
            return None
    
    def rollback_update(self, update_id: str) -> bool:
        """Rollback a configuration update."""
        try:
            update = self.get_update_status(update_id)
            if not update:
                self.logger.error(f"Update {update_id} not found for rollback")
                return False
            
            if update.status != UpdateStatus.COMPLETED:
                self.logger.error(f"Update {update_id} cannot be rolled back (status: {update.status})")
                return False
            
            if not update.rollback_data or "snapshot_id" not in update.rollback_data:
                self.logger.error(f"No rollback data available for update {update_id}")
                return False
            
            snapshot_id = update.rollback_data["snapshot_id"]
            if snapshot_id not in self.config_snapshots:
                self.logger.error(f"Snapshot {snapshot_id} not found for rollback")
                return False
            
            # Restore from snapshot
            snapshot_config = self.config_snapshots[snapshot_id]
            snapshot_dict = asdict(snapshot_config)
            
            success = self.config_manager.update_config(**snapshot_dict)
            if success:
                update.status = UpdateStatus.ROLLED_BACK
                self.logger.info(f"Update {update_id} rolled back successfully")
                return True
            else:
                self.logger.error(f"Failed to rollback update {update_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error rolling back update {update_id}: {e}")
            return False
    
    def _check_auto_rollback(self, update_id: str):
        """Check if an update should be automatically rolled back."""
        try:
            update = self.get_update_status(update_id)
            if not update or update.status != UpdateStatus.COMPLETED:
                return
            
            # Check if system is healthy after the update
            if not self._is_system_healthy():
                self.logger.warning(f"System unhealthy after update {update_id}, initiating auto-rollback")
                self.rollback_update(update_id)
            
        except Exception as e:
            self.logger.error(f"Error in auto-rollback check for {update_id}: {e}")
    
    def _is_system_healthy(self) -> bool:
        """Check if the system is healthy after a configuration update."""
        try:
            # Basic health checks
            config = self.config_manager.get_config()
            
            # Validate current configuration
            validation_report = self.validator.validate_config(config)
            if not validation_report.is_valid:
                return False
            
            # Check if critical components are responsive
            # This would typically involve checking if detection and correction systems are working
            # For now, we'll do basic validation
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return False
    
    def _start_update_monitor(self):
        """Start background monitoring of updates."""
        def monitor():
            while True:
                try:
                    # Clean up old snapshots
                    self._cleanup_old_snapshots()
                    
                    # Check for stuck updates
                    self._check_stuck_updates()
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    self.logger.error(f"Update monitor error: {e}")
                    time.sleep(300)  # Wait longer on error
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _cleanup_old_snapshots(self):
        """Clean up old configuration snapshots."""
        try:
            if len(self.config_snapshots) <= self.max_snapshots:
                return
            
            # Keep only the most recent snapshots
            # This is a simple implementation - in production, you might want more sophisticated cleanup
            snapshot_ids = list(self.config_snapshots.keys())
            old_snapshots = snapshot_ids[:-self.max_snapshots]
            
            for snapshot_id in old_snapshots:
                del self.config_snapshots[snapshot_id]
            
            self.logger.debug(f"Cleaned up {len(old_snapshots)} old snapshots")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up snapshots: {e}")
    
    def _check_stuck_updates(self):
        """Check for updates that are stuck in processing."""
        try:
            current_time = datetime.now()
            stuck_timeout = timedelta(minutes=10)
            
            with self._lock:
                stuck_updates = []
                for update_id, update in self.pending_updates.items():
                    if (current_time - update.timestamp) > stuck_timeout:
                        if update.status in [UpdateStatus.VALIDATING, UpdateStatus.APPLYING]:
                            stuck_updates.append(update_id)
                
                for update_id in stuck_updates:
                    update = self.pending_updates[update_id]
                    update.status = UpdateStatus.FAILED
                    update.error_message = "Update timed out"
                    self.logger.error(f"Update {update_id} marked as failed due to timeout")
                    
                    # Move to history
                    self.update_history.append(self.pending_updates.pop(update_id))
            
        except Exception as e:
            self.logger.error(f"Error checking stuck updates: {e}")
    
    def add_pre_update_callback(self, callback: Callable[[ConfigUpdate], bool]):
        """Add a pre-update callback that can veto updates."""
        self.pre_update_callbacks.append(callback)
    
    def add_post_update_callback(self, callback: Callable[[ConfigUpdate], None]):
        """Add a post-update callback for notifications."""
        self.post_update_callbacks.append(callback)
    
    def get_pending_updates(self) -> List[ConfigUpdate]:
        """Get list of pending updates."""
        with self._lock:
            return [deepcopy(update) for update in self.pending_updates.values()]
    
    def get_update_history(self, limit: Optional[int] = None) -> List[ConfigUpdate]:
        """Get update history."""
        with self._lock:
            history = sorted(self.update_history, key=lambda x: x.timestamp, reverse=True)
            return history[:limit] if limit else history
    
    def cancel_update(self, update_id: str) -> bool:
        """Cancel a pending update."""
        try:
            with self._lock:
                if update_id not in self.pending_updates:
                    return False
                
                update = self.pending_updates[update_id]
                if update.status in [UpdateStatus.APPLYING, UpdateStatus.COMPLETED]:
                    return False  # Cannot cancel updates that are already applying or completed
                
                update.status = UpdateStatus.FAILED
                update.error_message = "Update cancelled by user"
                
                # Move to history
                self.update_history.append(self.pending_updates.pop(update_id))
                
                self.logger.info(f"Update {update_id} cancelled")
                return True
                
        except Exception as e:
            self.logger.error(f"Error cancelling update {update_id}: {e}")
            return False
    
    def analyze_update_impact(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the potential impact of configuration changes."""
        return self.config_manager.analyze_change_impact(changes)
    
    def get_rollback_info(self, update_id: str) -> Optional[Dict[str, Any]]:
        """Get rollback information for an update."""
        update = self.get_update_status(update_id)
        if not update or not update.rollback_data:
            return None
        
        snapshot_id = update.rollback_data.get("snapshot_id")
        if not snapshot_id or snapshot_id not in self.config_snapshots:
            return None
        
        return {
            "update_id": update_id,
            "snapshot_id": snapshot_id,
            "rollback_available": True,
            "snapshot_timestamp": update.timestamp,
            "changes_to_rollback": update.changes
        }


# Global runtime updater instance
_runtime_updater: Optional[RuntimeConfigUpdater] = None


def get_runtime_updater(config_manager: Optional[ConfigManager] = None) -> RuntimeConfigUpdater:
    """Get the global runtime configuration updater instance."""
    global _runtime_updater
    if _runtime_updater is None:
        if config_manager is None:
            from .config_manager import get_config_manager
            config_manager = get_config_manager()
        _runtime_updater = RuntimeConfigUpdater(config_manager)
    return _runtime_updater


def request_config_update(changes: Dict[str, Any], requester: str = "system", 
                         reason: str = "Runtime update") -> str:
    """Request a configuration update."""
    return get_runtime_updater().request_update(changes, requester, reason)


def get_update_status(update_id: str) -> Optional[ConfigUpdate]:
    """Get the status of a configuration update."""
    return get_runtime_updater().get_update_status(update_id)


def rollback_update(update_id: str) -> bool:
    """Rollback a configuration update."""
    return get_runtime_updater().rollback_update(update_id)