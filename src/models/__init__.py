"""
Models package for the werewolf game system.
"""

from .player import Player, Role, Team, PlayerStatus
from .llm_player import LLMPlayer
from .hallucination_models import (
    # Enums
    HallucinationType,
    HallucinationSeverity,
    
    # Speech tracking data structures
    SpeechRecord,
    ReferenceInfo,
    
    # Hallucination detection data structures
    TextLocation,
    Hallucination,
    HallucinationResult,
    FalseReference,
    IdentityIssue,
    TemporalError,
    FabricatedInteraction,
    
    # Speech correction data structures
    Correction,
    CorrectionResult,
    
    # Reporting data structures
    PlayerHallucinationStats,
    GameHallucinationStats,
    HallucinationReport,
    PlayerHallucinationReport,
    
    # Configuration
    HallucinationReductionConfig,
    
    # Exceptions
    HallucinationDetectionError,
    SpeechCorrectionError,
    ContextBuildingError,
    SpeechHistoryError,
    ReportGenerationError,
)

__all__ = [
    # Player models
    "Player",
    "Role", 
    "Team",
    "PlayerStatus",
    "LLMPlayer",
    
    # Hallucination detection enums
    "HallucinationType",
    "HallucinationSeverity",
    
    # Speech tracking
    "SpeechRecord",
    "ReferenceInfo",
    
    # Hallucination detection
    "TextLocation",
    "Hallucination",
    "HallucinationResult",
    "FalseReference",
    "IdentityIssue",
    "TemporalError",
    "FabricatedInteraction",
    
    # Speech correction
    "Correction",
    "CorrectionResult",
    
    # Reporting
    "PlayerHallucinationStats",
    "GameHallucinationStats",
    "HallucinationReport",
    "PlayerHallucinationReport",
    
    # Configuration
    "HallucinationReductionConfig",
    
    # Exceptions
    "HallucinationDetectionError",
    "SpeechCorrectionError",
    "ContextBuildingError",
    "SpeechHistoryError",
    "ReportGenerationError",
]