"""
Core data models and types for the hallucination detection and correction system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel


# Enumerations for hallucination detection
class HallucinationType(Enum):
    """Types of hallucinations that can be detected."""
    FALSE_REFERENCE = "false_reference"
    IDENTITY_INCONSISTENCY = "identity_inconsistency"
    TEMPORAL_ERROR = "temporal_error"
    FABRICATED_INTERACTION = "fabricated_interaction"
    INVALID_CLAIM = "invalid_claim"


class HallucinationSeverity(Enum):
    """Severity levels for detected hallucinations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Data structures for speech tracking
@dataclass
class SpeechRecord:
    """Record of a player's speech in the game."""
    player_id: int
    player_name: str
    speech_content: str
    round_number: int
    phase: str
    timestamp: datetime
    speaking_order: int


@dataclass
class ReferenceInfo:
    """Information about available references for speech validation."""
    player_id: int
    player_name: str
    speech_content: str
    round_number: int
    phase: str
    is_available: bool


# Data structures for hallucination detection
@dataclass
class TextLocation:
    """Location of text within a speech."""
    start_index: int
    end_index: int
    text: str


@dataclass
class Hallucination:
    """Represents a detected hallucination in player speech."""
    type: HallucinationType
    description: str
    location: TextLocation
    severity: HallucinationSeverity
    suggested_correction: str


@dataclass
class HallucinationResult:
    """Result of hallucination detection analysis."""
    is_valid: bool
    hallucination_count: int
    hallucinations: List[Hallucination]
    confidence_score: float
    correction_needed: bool


# Data structures for specific hallucination types
@dataclass
class FalseReference:
    """Represents a false reference to another player's speech."""
    claimed_speaker: str
    claimed_content: str
    actual_content: Optional[str]
    location: TextLocation


@dataclass
class IdentityIssue:
    """Represents an identity-related inconsistency."""
    player_mentioned: str
    claimed_identity: str
    actual_identity: Optional[str]
    location: TextLocation


@dataclass
class TemporalError:
    """Represents a temporal reference error."""
    claimed_time_reference: str
    actual_time_context: str
    location: TextLocation


@dataclass
class FabricatedInteraction:
    """Represents a fabricated interaction between players."""
    involved_players: List[str]
    claimed_interaction: str
    location: TextLocation


# Data structures for speech correction
@dataclass
class Correction:
    """Represents a correction applied to speech."""
    type: HallucinationType
    original_text: str
    corrected_text: str
    reason: str


@dataclass
class CorrectionResult:
    """Result of speech correction process."""
    original_speech: str
    corrected_speech: str
    corrections_applied: List[Correction]
    success: bool
    quality_score: float


# Data structures for reporting
@dataclass
class PlayerHallucinationStats:
    """Statistics for a player's hallucinations."""
    player_id: int
    player_name: str
    total_speeches: int
    hallucination_count: int
    hallucination_rate: float
    hallucinations_by_type: Dict[HallucinationType, int]
    corrections_applied: int
    correction_success_rate: float


@dataclass
class GameHallucinationStats:
    """Overall game hallucination statistics."""
    game_id: str
    total_speeches: int
    total_hallucinations: int
    overall_hallucination_rate: float
    hallucinations_by_type: Dict[HallucinationType, int]
    corrections_applied: int
    correction_success_rate: float


@dataclass
class HallucinationReport:
    """Comprehensive hallucination report for a game."""
    game_id: str
    generation_time: datetime
    game_stats: GameHallucinationStats
    player_stats: List[PlayerHallucinationStats]
    detailed_cases: List[Dict[str, Any]]
    summary: str


@dataclass
class PlayerHallucinationReport:
    """Detailed hallucination report for a specific player."""
    player_id: int
    player_name: str
    generation_time: datetime
    stats: PlayerHallucinationStats
    detailed_cases: List[Dict[str, Any]]
    improvement_suggestions: List[str]


# Configuration classes
@dataclass
class HallucinationReductionConfig:
    """Configuration for the hallucination reduction system."""
    # Detection configuration
    detection_strictness: float = 0.8
    enable_multi_layer_detection: bool = True
    max_detection_time: float = 5.0
    
    # Correction configuration
    enable_auto_correction: bool = True
    max_correction_attempts: int = 3
    correction_quality_threshold: float = 0.7
    
    # Context configuration
    max_speech_history_length: int = 100
    enable_reality_anchors: bool = True
    context_validation_enabled: bool = True
    
    # Reporting configuration
    enable_detailed_logging: bool = True
    report_generation_enabled: bool = True
    export_format: str = "json"
    
    # Performance configuration
    enable_async_processing: bool = True
    cache_detection_results: bool = True
    max_concurrent_detections: int = 5


# Exception classes
class HallucinationDetectionError(Exception):
    """Exception raised during hallucination detection process."""
    
    def __init__(self, message: str, player_id: Optional[int] = None, speech: Optional[str] = None):
        super().__init__(message)
        self.player_id = player_id
        self.speech = speech


class SpeechCorrectionError(Exception):
    """Exception raised during speech correction process."""
    
    def __init__(self, message: str, original_speech: Optional[str] = None, correction_attempt: Optional[int] = None):
        super().__init__(message)
        self.original_speech = original_speech
        self.correction_attempt = correction_attempt


class ContextBuildingError(Exception):
    """Exception raised during context building process."""
    
    def __init__(self, message: str, player_id: Optional[int] = None, phase: Optional[str] = None):
        super().__init__(message)
        self.player_id = player_id
        self.phase = phase


class SpeechHistoryError(Exception):
    """Exception raised during speech history operations."""
    
    def __init__(self, message: str, player_id: Optional[int] = None, round_number: Optional[int] = None):
        super().__init__(message)
        self.player_id = player_id
        self.round_number = round_number


class ReportGenerationError(Exception):
    """Exception raised during report generation process."""
    
    def __init__(self, message: str, report_type: Optional[str] = None, game_id: Optional[str] = None):
        super().__init__(message)
        self.report_type = report_type
        self.game_id = game_id