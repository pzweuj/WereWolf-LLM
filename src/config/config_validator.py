"""
Configuration validation utilities for the hallucination reduction system.
Provides comprehensive validation, schema checking, and configuration testing.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from pathlib import Path

from ..models.hallucination_models import HallucinationReductionConfig


@dataclass
class ValidationRule:
    """Represents a validation rule for configuration values."""
    field_name: str
    required: bool = True
    data_type: type = str
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[callable] = None
    description: str = ""


@dataclass
class ValidationIssue:
    """Represents a validation issue found in configuration."""
    level: str  # 'error', 'warning', 'info'
    field: str
    message: str
    current_value: Any = None
    suggested_value: Any = None


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    is_valid: bool
    issues: List[ValidationIssue]
    score: float  # 0.0 to 1.0, higher is better
    summary: str


class ConfigValidator:
    """
    Validates configuration for the hallucination reduction system.
    Provides schema validation, value checking, and configuration testing.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._create_validation_rules()
    
    def _create_validation_rules(self) -> List[ValidationRule]:
        """Create validation rules for configuration fields."""
        return [
            ValidationRule(
                field_name="detection_strictness",
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                description="Controls how strict the hallucination detection is"
            ),
            ValidationRule(
                field_name="enable_multi_layer_detection",
                data_type=bool,
                description="Whether to enable multi-layer hallucination detection"
            ),
            ValidationRule(
                field_name="max_detection_time",
                data_type=float,
                min_value=0.1,
                max_value=60.0,
                description="Maximum time allowed for hallucination detection (seconds)"
            ),
            ValidationRule(
                field_name="enable_auto_correction",
                data_type=bool,
                description="Whether to automatically correct detected hallucinations"
            ),
            ValidationRule(
                field_name="max_correction_attempts",
                data_type=int,
                min_value=1,
                max_value=10,
                description="Maximum number of correction attempts per speech"
            ),
            ValidationRule(
                field_name="correction_quality_threshold",
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                description="Minimum quality score required for corrections"
            ),
            ValidationRule(
                field_name="max_speech_history_length",
                data_type=int,
                min_value=10,
                max_value=1000,
                description="Maximum number of speeches to keep in history"
            ),
            ValidationRule(
                field_name="enable_reality_anchors",
                data_type=bool,
                description="Whether to add reality anchors to context"
            ),
            ValidationRule(
                field_name="context_validation_enabled",
                data_type=bool,
                description="Whether to validate context completeness"
            ),
            ValidationRule(
                field_name="enable_detailed_logging",
                data_type=bool,
                description="Whether to enable detailed logging"
            ),
            ValidationRule(
                field_name="report_generation_enabled",
                data_type=bool,
                description="Whether to generate hallucination reports"
            ),
            ValidationRule(
                field_name="export_format",
                data_type=str,
                allowed_values=["json", "csv", "html", "xml"],
                description="Format for exporting reports"
            ),
            ValidationRule(
                field_name="enable_async_processing",
                data_type=bool,
                description="Whether to enable asynchronous processing"
            ),
            ValidationRule(
                field_name="cache_detection_results",
                data_type=bool,
                description="Whether to cache detection results"
            ),
            ValidationRule(
                field_name="max_concurrent_detections",
                data_type=int,
                min_value=1,
                max_value=20,
                description="Maximum number of concurrent detection processes"
            )
        ]
    
    def validate_config(self, config: Union[HallucinationReductionConfig, Dict[str, Any]]) -> ValidationReport:
        """Validate a configuration object or dictionary."""
        if isinstance(config, HallucinationReductionConfig):
            config_dict = config.__dict__
        else:
            config_dict = config
        
        issues = []
        
        # Check each validation rule
        for rule in self.validation_rules:
            field_issues = self._validate_field(config_dict, rule)
            issues.extend(field_issues)
        
        # Check for unknown fields
        known_fields = {rule.field_name for rule in self.validation_rules}
        for field in config_dict:
            if field not in known_fields and not field.startswith('_'):
                issues.append(ValidationIssue(
                    level="warning",
                    field=field,
                    message=f"Unknown configuration field: {field}",
                    current_value=config_dict[field]
                ))
        
        # Perform cross-field validation
        cross_field_issues = self._validate_cross_field_constraints(config_dict)
        issues.extend(cross_field_issues)
        
        # Calculate validation score
        score = self._calculate_validation_score(issues)
        
        # Determine if configuration is valid
        error_count = sum(1 for issue in issues if issue.level == "error")
        is_valid = error_count == 0
        
        # Generate summary
        summary = self._generate_validation_summary(issues, score)
        
        return ValidationReport(
            is_valid=is_valid,
            issues=issues,
            score=score,
            summary=summary
        )
    
    def _validate_field(self, config_dict: Dict[str, Any], rule: ValidationRule) -> List[ValidationIssue]:
        """Validate a single configuration field."""
        issues = []
        field_name = rule.field_name
        
        # Check if field exists
        if field_name not in config_dict:
            if rule.required:
                issues.append(ValidationIssue(
                    level="error",
                    field=field_name,
                    message=f"Required field '{field_name}' is missing",
                    suggested_value=self._get_default_value(rule)
                ))
            return issues
        
        value = config_dict[field_name]
        
        # Check data type
        if not isinstance(value, rule.data_type):
            issues.append(ValidationIssue(
                level="error",
                field=field_name,
                message=f"Field '{field_name}' must be of type {rule.data_type.__name__}, got {type(value).__name__}",
                current_value=value,
                suggested_value=self._get_default_value(rule)
            ))
            return issues
        
        # Check value range for numeric types
        if rule.min_value is not None and isinstance(value, (int, float)):
            if value < rule.min_value:
                issues.append(ValidationIssue(
                    level="error",
                    field=field_name,
                    message=f"Field '{field_name}' must be >= {rule.min_value}, got {value}",
                    current_value=value,
                    suggested_value=rule.min_value
                ))
        
        if rule.max_value is not None and isinstance(value, (int, float)):
            if value > rule.max_value:
                issues.append(ValidationIssue(
                    level="error",
                    field=field_name,
                    message=f"Field '{field_name}' must be <= {rule.max_value}, got {value}",
                    current_value=value,
                    suggested_value=rule.max_value
                ))
        
        # Check allowed values
        if rule.allowed_values is not None:
            if value not in rule.allowed_values:
                issues.append(ValidationIssue(
                    level="error",
                    field=field_name,
                    message=f"Field '{field_name}' must be one of {rule.allowed_values}, got {value}",
                    current_value=value,
                    suggested_value=rule.allowed_values[0]
                ))
        
        # Run custom validator
        if rule.custom_validator is not None:
            try:
                custom_result = rule.custom_validator(value)
                if custom_result is not True:
                    issues.append(ValidationIssue(
                        level="error",
                        field=field_name,
                        message=f"Custom validation failed for '{field_name}': {custom_result}",
                        current_value=value
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    level="warning",
                    field=field_name,
                    message=f"Custom validator error for '{field_name}': {e}",
                    current_value=value
                ))
        
        # Add performance warnings
        performance_issues = self._check_performance_implications(field_name, value)
        issues.extend(performance_issues)
        
        return issues
    
    def _validate_cross_field_constraints(self, config_dict: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate constraints that involve multiple fields."""
        issues = []
        
        # Check if correction is enabled but detection is disabled
        if (config_dict.get("enable_auto_correction", True) and 
            not config_dict.get("enable_multi_layer_detection", True)):
            issues.append(ValidationIssue(
                level="warning",
                field="enable_auto_correction",
                message="Auto correction is enabled but multi-layer detection is disabled",
                current_value=config_dict.get("enable_auto_correction")
            ))
        
        # Check if async processing is enabled with high concurrent detections
        if (config_dict.get("enable_async_processing", True) and 
            config_dict.get("max_concurrent_detections", 5) > 10):
            issues.append(ValidationIssue(
                level="info",
                field="max_concurrent_detections",
                message="High concurrent detections with async processing may impact performance",
                current_value=config_dict.get("max_concurrent_detections")
            ))
        
        # Check detection time vs correction attempts
        detection_time = config_dict.get("max_detection_time", 5.0)
        correction_attempts = config_dict.get("max_correction_attempts", 3)
        if detection_time * correction_attempts > 30.0:
            issues.append(ValidationIssue(
                level="warning",
                field="max_detection_time",
                message="Total detection and correction time may be too high for real-time gameplay",
                current_value=detection_time
            ))
        
        return issues
    
    def _check_performance_implications(self, field_name: str, value: Any) -> List[ValidationIssue]:
        """Check for performance implications of configuration values."""
        issues = []
        
        if field_name == "max_speech_history_length" and value > 500:
            issues.append(ValidationIssue(
                level="info",
                field=field_name,
                message="Large speech history may impact memory usage and performance",
                current_value=value,
                suggested_value=200
            ))
        
        if field_name == "max_detection_time" and value > 10.0:
            issues.append(ValidationIssue(
                level="warning",
                field=field_name,
                message="High detection timeout may impact game flow and user experience",
                current_value=value,
                suggested_value=5.0
            ))
        
        if field_name == "detection_strictness":
            if value > 0.95:
                issues.append(ValidationIssue(
                    level="info",
                    field=field_name,
                    message="Very high detection strictness may increase false positives",
                    current_value=value
                ))
            elif value < 0.3:
                issues.append(ValidationIssue(
                    level="warning",
                    field=field_name,
                    message="Very low detection strictness may miss real hallucinations",
                    current_value=value
                ))
        
        return issues
    
    def _get_default_value(self, rule: ValidationRule) -> Any:
        """Get default value for a validation rule."""
        default_config = HallucinationReductionConfig()
        return getattr(default_config, rule.field_name, None)
    
    def _calculate_validation_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate a validation score based on issues found."""
        if not issues:
            return 1.0
        
        # Weight different issue levels
        weights = {"error": -0.3, "warning": -0.1, "info": -0.05}
        
        total_penalty = sum(weights.get(issue.level, 0) for issue in issues)
        score = max(0.0, 1.0 + total_penalty)
        
        return round(score, 2)
    
    def _generate_validation_summary(self, issues: List[ValidationIssue], score: float) -> str:
        """Generate a human-readable validation summary."""
        if not issues:
            return "Configuration is valid with no issues found."
        
        error_count = sum(1 for issue in issues if issue.level == "error")
        warning_count = sum(1 for issue in issues if issue.level == "warning")
        info_count = sum(1 for issue in issues if issue.level == "info")
        
        summary_parts = []
        
        if error_count > 0:
            summary_parts.append(f"{error_count} error(s)")
        if warning_count > 0:
            summary_parts.append(f"{warning_count} warning(s)")
        if info_count > 0:
            summary_parts.append(f"{info_count} info message(s)")
        
        summary = f"Validation completed with {', '.join(summary_parts)}. Score: {score:.2f}/1.0"
        
        if error_count > 0:
            summary += " - Configuration is invalid and requires fixes."
        elif warning_count > 0:
            summary += " - Configuration is valid but has potential issues."
        else:
            summary += " - Configuration is valid with minor suggestions."
        
        return summary
    
    def validate_config_file(self, file_path: str) -> ValidationReport:
        """Validate a configuration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Remove metadata if present
            config_data = {k: v for k, v in config_data.items() if not k.startswith('_')}
            
            return self.validate_config(config_data)
            
        except FileNotFoundError:
            return ValidationReport(
                is_valid=False,
                issues=[ValidationIssue(
                    level="error",
                    field="file",
                    message=f"Configuration file not found: {file_path}"
                )],
                score=0.0,
                summary=f"Configuration file not found: {file_path}"
            )
        except json.JSONDecodeError as e:
            return ValidationReport(
                is_valid=False,
                issues=[ValidationIssue(
                    level="error",
                    field="file",
                    message=f"Invalid JSON format: {e}"
                )],
                score=0.0,
                summary=f"Invalid JSON format in configuration file"
            )
        except Exception as e:
            return ValidationReport(
                is_valid=False,
                issues=[ValidationIssue(
                    level="error",
                    field="file",
                    message=f"Error reading configuration file: {e}"
                )],
                score=0.0,
                summary=f"Error reading configuration file: {e}"
            )
    
    def generate_config_schema(self) -> Dict[str, Any]:
        """Generate a JSON schema for the configuration."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Hallucination Reduction Configuration",
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for rule in self.validation_rules:
            prop_schema = {
                "description": rule.description
            }
            
            # Add type information
            if rule.data_type == bool:
                prop_schema["type"] = "boolean"
            elif rule.data_type == int:
                prop_schema["type"] = "integer"
            elif rule.data_type == float:
                prop_schema["type"] = "number"
            elif rule.data_type == str:
                prop_schema["type"] = "string"
            
            # Add constraints
            if rule.min_value is not None:
                prop_schema["minimum"] = rule.min_value
            if rule.max_value is not None:
                prop_schema["maximum"] = rule.max_value
            if rule.allowed_values is not None:
                prop_schema["enum"] = rule.allowed_values
            
            schema["properties"][rule.field_name] = prop_schema
            
            if rule.required:
                schema["required"].append(rule.field_name)
        
        return schema
    
    def fix_config_issues(self, config_dict: Dict[str, Any], 
                         validation_report: ValidationReport) -> Tuple[Dict[str, Any], List[str]]:
        """Attempt to automatically fix configuration issues."""
        fixed_config = config_dict.copy()
        fixes_applied = []
        
        for issue in validation_report.issues:
            if issue.level == "error" and issue.suggested_value is not None:
                fixed_config[issue.field] = issue.suggested_value
                fixes_applied.append(f"Fixed {issue.field}: {issue.current_value} -> {issue.suggested_value}")
        
        return fixed_config, fixes_applied


# Global validator instance
_validator: Optional[ConfigValidator] = None


def get_validator() -> ConfigValidator:
    """Get the global configuration validator instance."""
    global _validator
    if _validator is None:
        _validator = ConfigValidator()
    return _validator


def validate_config(config: Union[HallucinationReductionConfig, Dict[str, Any]]) -> ValidationReport:
    """Validate a configuration object or dictionary."""
    return get_validator().validate_config(config)


def validate_config_file(file_path: str) -> ValidationReport:
    """Validate a configuration file."""
    return get_validator().validate_config_file(file_path)