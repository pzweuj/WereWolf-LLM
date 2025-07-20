"""
Configuration management system for the hallucination reduction feature.
Provides configuration loading, validation, runtime updates, and change impact analysis.
"""

import json
import os
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from copy import deepcopy

from ..models.hallucination_models import HallucinationReductionConfig


@dataclass
class ConfigChangeEvent:
    """Represents a configuration change event."""
    timestamp: datetime
    config_key: str
    old_value: Any
    new_value: Any
    source: str  # 'file', 'runtime', 'api'
    impact_level: str  # 'low', 'medium', 'high', 'critical'


@dataclass
class ConfigValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class ConfigManager:
    """
    Manages configuration for the hallucination reduction system.
    Supports loading, validation, runtime updates, and change tracking.
    """
    
    def __init__(self, config_file: str = "config/hallucination_config.json"):
        self.config_file = Path(config_file)
        self.config: HallucinationReductionConfig = HallucinationReductionConfig()
        self.change_history: List[ConfigChangeEvent] = []
        self.change_listeners: List[Callable[[ConfigChangeEvent], None]] = []
        self._lock = threading.RLock()
        self._file_watcher_active = False
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Load initial configuration
        self._load_config()
        
        # Start file watcher if config file exists
        if self.config_file.exists():
            self._start_file_watcher()
    
    def _load_config(self) -> bool:
        """Load configuration from file."""
        try:
            if not self.config_file.exists():
                self.logger.info(f"Configuration file {self.config_file} not found, using defaults")
                self._save_default_config()
                return True
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate configuration data
            validation_result = self._validate_config_data(config_data)
            if not validation_result.is_valid:
                self.logger.error(f"Invalid configuration: {validation_result.errors}")
                return False
            
            # Update configuration
            old_config = deepcopy(self.config)
            self.config = HallucinationReductionConfig(**config_data)
            
            # Track changes
            self._track_config_changes(old_config, self.config, 'file')
            
            self.logger.info(f"Configuration loaded from {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False
    
    def _save_default_config(self):
        """Save default configuration to file."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = asdict(self.config)
            config_data['_metadata'] = {
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'description': 'Hallucination reduction system configuration'
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Default configuration saved to {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save default configuration: {e}")
    
    def _validate_config_data(self, config_data: Dict[str, Any]) -> ConfigValidationResult:
        """Validate configuration data."""
        errors = []
        warnings = []
        suggestions = []
        
        # Remove metadata if present
        config_data = {k: v for k, v in config_data.items() if not k.startswith('_')}
        
        # Check required fields and types
        expected_fields = {
            'detection_strictness': (float, 0.0, 1.0),
            'enable_multi_layer_detection': (bool,),
            'max_detection_time': (float, 0.1, 60.0),
            'enable_auto_correction': (bool,),
            'max_correction_attempts': (int, 1, 10),
            'correction_quality_threshold': (float, 0.0, 1.0),
            'max_speech_history_length': (int, 10, 1000),
            'enable_reality_anchors': (bool,),
            'context_validation_enabled': (bool,),
            'enable_detailed_logging': (bool,),
            'report_generation_enabled': (bool,),
            'export_format': (str,),
            'enable_async_processing': (bool,),
            'cache_detection_results': (bool,),
            'max_concurrent_detections': (int, 1, 20)
        }
        
        for field, constraints in expected_fields.items():
            if field not in config_data:
                warnings.append(f"Missing field '{field}', will use default value")
                continue
            
            value = config_data[field]
            expected_type = constraints[0]
            
            # Type validation
            if not isinstance(value, expected_type):
                errors.append(f"Field '{field}' must be of type {expected_type.__name__}, got {type(value).__name__}")
                continue
            
            # Range validation for numeric types
            if len(constraints) > 1 and isinstance(value, (int, float)):
                min_val, max_val = constraints[1], constraints[2]
                if not (min_val <= value <= max_val):
                    errors.append(f"Field '{field}' must be between {min_val} and {max_val}, got {value}")
        
        # Specific validations
        if 'export_format' in config_data:
            valid_formats = ['json', 'csv', 'html', 'xml']
            if config_data['export_format'] not in valid_formats:
                errors.append(f"export_format must be one of {valid_formats}")
        
        # Performance suggestions
        if config_data.get('max_detection_time', 5.0) > 10.0:
            suggestions.append("Consider reducing max_detection_time for better performance")
        
        if config_data.get('max_speech_history_length', 100) > 500:
            suggestions.append("Large speech history may impact memory usage")
        
        return ConfigValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _track_config_changes(self, old_config: HallucinationReductionConfig, 
                            new_config: HallucinationReductionConfig, source: str):
        """Track configuration changes."""
        old_dict = asdict(old_config)
        new_dict = asdict(new_config)
        
        for key, new_value in new_dict.items():
            old_value = old_dict.get(key)
            if old_value != new_value:
                impact_level = self._assess_change_impact(key, old_value, new_value)
                
                change_event = ConfigChangeEvent(
                    timestamp=datetime.now(),
                    config_key=key,
                    old_value=old_value,
                    new_value=new_value,
                    source=source,
                    impact_level=impact_level
                )
                
                self.change_history.append(change_event)
                self._notify_change_listeners(change_event)
    
    def _assess_change_impact(self, key: str, old_value: Any, new_value: Any) -> str:
        """Assess the impact level of a configuration change."""
        # Critical changes that require restart or major reconfiguration
        critical_keys = ['enable_multi_layer_detection', 'enable_auto_correction']
        if key in critical_keys:
            return 'critical'
        
        # High impact changes that affect core functionality
        high_impact_keys = ['detection_strictness', 'correction_quality_threshold', 'max_correction_attempts']
        if key in high_impact_keys:
            return 'high'
        
        # Medium impact changes that affect performance or behavior
        medium_impact_keys = ['max_detection_time', 'max_speech_history_length', 'enable_async_processing']
        if key in medium_impact_keys:
            return 'medium'
        
        # Low impact changes (logging, reporting, etc.)
        return 'low'
    
    def _notify_change_listeners(self, change_event: ConfigChangeEvent):
        """Notify registered change listeners."""
        for listener in self.change_listeners:
            try:
                listener(change_event)
            except Exception as e:
                self.logger.error(f"Error notifying change listener: {e}")
    
    def _start_file_watcher(self):
        """Start watching configuration file for changes."""
        # Simple file modification time checking
        # In production, consider using watchdog library for better file watching
        self._file_watcher_active = True
        self._last_modified = self.config_file.stat().st_mtime
        
        def watch_file():
            while self._file_watcher_active:
                try:
                    if self.config_file.exists():
                        current_modified = self.config_file.stat().st_mtime
                        if current_modified > self._last_modified:
                            self.logger.info("Configuration file changed, reloading...")
                            self._load_config()
                            self._last_modified = current_modified
                    
                    threading.Event().wait(1.0)  # Check every second
                    
                except Exception as e:
                    self.logger.error(f"File watcher error: {e}")
                    threading.Event().wait(5.0)  # Wait longer on error
        
        watcher_thread = threading.Thread(target=watch_file, daemon=True)
        watcher_thread.start()
    
    def get_config(self) -> HallucinationReductionConfig:
        """Get current configuration."""
        with self._lock:
            return deepcopy(self.config)
    
    def update_config(self, **kwargs) -> bool:
        """Update configuration at runtime."""
        try:
            with self._lock:
                # Validate new values
                test_config_data = asdict(self.config)
                test_config_data.update(kwargs)
                
                validation_result = self._validate_config_data(test_config_data)
                if not validation_result.is_valid:
                    self.logger.error(f"Invalid configuration update: {validation_result.errors}")
                    return False
                
                # Apply changes
                old_config = deepcopy(self.config)
                for key, value in kwargs.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
                    else:
                        self.logger.warning(f"Unknown configuration key: {key}")
                
                # Track changes
                self._track_config_changes(old_config, self.config, 'runtime')
                
                self.logger.info(f"Configuration updated: {kwargs}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            with self._lock:
                config_data = asdict(self.config)
                config_data['_metadata'] = {
                    'version': '1.0',
                    'updated_at': datetime.now().isoformat(),
                    'description': 'Hallucination reduction system configuration'
                }
                
                # Ensure directory exists
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Configuration saved to {self.config_file}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def reload_config(self) -> bool:
        """Reload configuration from file."""
        with self._lock:
            return self._load_config()
    
    def add_change_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """Add a configuration change listener."""
        self.change_listeners.append(listener)
    
    def remove_change_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """Remove a configuration change listener."""
        if listener in self.change_listeners:
            self.change_listeners.remove(listener)
    
    def get_change_history(self, limit: Optional[int] = None) -> List[ConfigChangeEvent]:
        """Get configuration change history."""
        with self._lock:
            history = sorted(self.change_history, key=lambda x: x.timestamp, reverse=True)
            return history[:limit] if limit else history
    
    def analyze_change_impact(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the potential impact of configuration changes."""
        impact_analysis = {
            'overall_impact': 'low',
            'affected_components': [],
            'restart_required': False,
            'performance_impact': 'minimal',
            'recommendations': []
        }
        
        critical_changes = []
        high_impact_changes = []
        
        for key, value in changes.items():
            current_value = getattr(self.config, key, None)
            impact_level = self._assess_change_impact(key, current_value, value)
            
            if impact_level == 'critical':
                critical_changes.append(key)
            elif impact_level == 'high':
                high_impact_changes.append(key)
        
        # Determine overall impact
        if critical_changes:
            impact_analysis['overall_impact'] = 'critical'
            impact_analysis['restart_required'] = True
            impact_analysis['affected_components'].extend(['detection_engine', 'correction_system'])
        elif high_impact_changes:
            impact_analysis['overall_impact'] = 'high'
            impact_analysis['performance_impact'] = 'moderate'
            impact_analysis['affected_components'].extend(['detection_accuracy', 'correction_quality'])
        
        # Add specific recommendations
        if 'detection_strictness' in changes:
            if changes['detection_strictness'] > 0.9:
                impact_analysis['recommendations'].append("High detection strictness may increase false positives")
            elif changes['detection_strictness'] < 0.5:
                impact_analysis['recommendations'].append("Low detection strictness may miss real hallucinations")
        
        if 'max_detection_time' in changes:
            if changes['max_detection_time'] > 10.0:
                impact_analysis['recommendations'].append("High detection timeout may impact game flow")
        
        return impact_analysis
    
    def export_config(self, format: str = 'json') -> str:
        """Export configuration in specified format."""
        config_data = asdict(self.config)
        
        if format.lower() == 'json':
            return json.dumps(config_data, indent=2, ensure_ascii=False)
        elif format.lower() == 'yaml':
            try:
                import yaml
                return yaml.dump(config_data, default_flow_style=False, allow_unicode=True)
            except ImportError:
                self.logger.error("PyYAML not installed, falling back to JSON")
                return json.dumps(config_data, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_config(self, config_str: str, format: str = 'json') -> bool:
        """Import configuration from string."""
        try:
            if format.lower() == 'json':
                config_data = json.loads(config_str)
            elif format.lower() == 'yaml':
                import yaml
                config_data = yaml.safe_load(config_str)
            else:
                raise ValueError(f"Unsupported import format: {format}")
            
            # Validate and apply
            validation_result = self._validate_config_data(config_data)
            if not validation_result.is_valid:
                self.logger.error(f"Invalid imported configuration: {validation_result.errors}")
                return False
            
            with self._lock:
                old_config = deepcopy(self.config)
                self.config = HallucinationReductionConfig(**config_data)
                self._track_config_changes(old_config, self.config, 'import')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import configuration: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values."""
        try:
            with self._lock:
                old_config = deepcopy(self.config)
                self.config = HallucinationReductionConfig()
                self._track_config_changes(old_config, self.config, 'reset')
                
                self.logger.info("Configuration reset to defaults")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to reset configuration: {e}")
            return False
    
    def stop_file_watcher(self):
        """Stop the file watcher."""
        self._file_watcher_active = False
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop_file_watcher()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: str = "config/hallucination_config.json") -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def get_config() -> HallucinationReductionConfig:
    """Get current configuration."""
    return get_config_manager().get_config()


def update_config(**kwargs) -> bool:
    """Update configuration at runtime."""
    return get_config_manager().update_config(**kwargs)