"""
Configuration management module for the hallucination reduction system.
Provides comprehensive configuration management, validation, and runtime updates.
"""

from .config_manager import (
    ConfigManager,
    ConfigChangeEvent,
    ConfigValidationResult,
    get_config_manager,
    get_config,
    update_config
)

from .config_validator import (
    ConfigValidator,
    ValidationRule,
    ValidationIssue,
    ValidationReport,
    get_validator,
    validate_config,
    validate_config_file
)

from .runtime_updater import (
    RuntimeConfigUpdater,
    ConfigUpdate,
    UpdateResult,
    UpdateStatus,
    get_runtime_updater,
    request_config_update,
    get_update_status,
    rollback_update
)

from .config_cli import ConfigCLI

__all__ = [
    # Config Manager
    'ConfigManager',
    'ConfigChangeEvent', 
    'ConfigValidationResult',
    'get_config_manager',
    'get_config',
    'update_config',
    
    # Config Validator
    'ConfigValidator',
    'ValidationRule',
    'ValidationIssue', 
    'ValidationReport',
    'get_validator',
    'validate_config',
    'validate_config_file',
    
    # Runtime Updater
    'RuntimeConfigUpdater',
    'ConfigUpdate',
    'UpdateResult',
    'UpdateStatus',
    'get_runtime_updater',
    'request_config_update',
    'get_update_status',
    'rollback_update',
    
    # CLI
    'ConfigCLI'
]