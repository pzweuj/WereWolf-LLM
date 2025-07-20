"""
Intelligent Speech Corrector for fixing hallucinations in LLM player speeches.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..models.hallucination_models import (
    HallucinationType,
    HallucinationSeverity,
    Hallucination,
    HallucinationResult,
    FalseReference,
    IdentityIssue,
    TemporalError,
    FabricatedInteraction,
    Correction,
    CorrectionResult,
    SpeechCorrectionError,
    HallucinationReductionConfig
)
from ..models.player import Player


class IntelligentSpeechCorrector:
    """
    Intelligent speech correction system that fixes detected hallucinations
    while preserving the original intent and game strategy.
    """
    
    def __init__(self, config: Optional[HallucinationReductionConfig] = None):
        """
        Initialize the speech corrector.
        
        Args:
            config: Configuration for speech correction
        """
        self.config = config or HallucinationReductionConfig()
        self._correction_strategies = {
            HallucinationType.FALSE_REFERENCE: self._correct_false_reference,
            HallucinationType.IDENTITY_INCONSISTENCY: self._correct_identity_inconsistency,
            HallucinationType.TEMPORAL_ERROR: self._correct_temporal_error,
            HallucinationType.FABRICATED_INTERACTION: self._correct_fabricated_interaction,
        }
    
    def correct_speech(
        self, 
        speech: str, 
        hallucinations: List[Hallucination], 
        context: Dict[str, Any],
        player: Optional[Player] = None
    ) -> CorrectionResult:
        """
        Correct a speech by fixing detected hallucinations.
        
        Args:
            speech: Original speech content
            hallucinations: List of detected hallucinations
            context: Game context information
            player: The speaking player (optional)
            
        Returns:
            CorrectionResult with corrected speech and applied corrections
        """
        try:
            if not hallucinations:
                return CorrectionResult(
                    original_speech=speech,
                    corrected_speech=speech,
                    corrections_applied=[],
                    success=True,
                    quality_score=1.0
                )
            
            corrected_speech = speech
            corrections_applied = []
            correction_attempts = 0
            
            # Sort hallucinations by location (reverse order to maintain indices)
            sorted_hallucinations = sorted(
                hallucinations, 
                key=lambda h: h.location.start_index, 
                reverse=True
            )
            
            for hallucination in sorted_hallucinations:
                if correction_attempts >= self.config.max_correction_attempts:
                    print(f"Warning: Maximum correction attempts ({self.config.max_correction_attempts}) reached")
                    break
                
                try:
                    correction_strategy = self._correction_strategies.get(hallucination.type)
                    if correction_strategy:
                        corrected_text, correction = correction_strategy(
                            corrected_speech, hallucination, context, player
                        )
                        
                        if corrected_text != corrected_speech:
                            corrected_speech = corrected_text
                            corrections_applied.append(correction)
                            correction_attempts += 1
                        
                except Exception as e:
                    print(f"Warning: Failed to correct hallucination {hallucination.type}: {e}")
                    continue
            
            # Validate correction quality
            quality_score = self._evaluate_correction_quality(
                speech, corrected_speech, corrections_applied
            )
            
            success = (
                quality_score >= self.config.correction_quality_threshold and
                len(corrections_applied) > 0
            )
            
            return CorrectionResult(
                original_speech=speech,
                corrected_speech=corrected_speech,
                corrections_applied=corrections_applied,
                success=success,
                quality_score=quality_score
            )
            
        except Exception as e:
            raise SpeechCorrectionError(
                f"Failed to correct speech: {str(e)}",
                original_speech=speech,
                correction_attempt=correction_attempts
            )
    
    def replace_false_references(
        self, 
        speech: str, 
        false_refs: List[FalseReference],
        context: Dict[str, Any]
    ) -> str:
        """
        Replace false references with generic expressions.
        
        Args:
            speech: Original speech
            false_refs: List of false references to replace
            context: Game context
            
        Returns:
            Speech with false references replaced
        """
        corrected_speech = speech
        
        # Sort by location (reverse order to maintain indices)
        sorted_refs = sorted(false_refs, key=lambda r: r.location.start_index, reverse=True)
        
        for false_ref in sorted_refs:
            replacement = self._generate_generic_reference_replacement(false_ref, context)
            
            corrected_speech = (
                corrected_speech[:false_ref.location.start_index] +
                replacement +
                corrected_speech[false_ref.location.end_index:]
            )
        
        return corrected_speech
    
    def fix_identity_claims(
        self, 
        speech: str, 
        identity_issues: List[IdentityIssue], 
        player: Optional[Player] = None
    ) -> str:
        """
        Fix identity claim inconsistencies.
        
        Args:
            speech: Original speech
            identity_issues: List of identity issues to fix
            player: The speaking player
            
        Returns:
            Speech with identity claims fixed
        """
        corrected_speech = speech
        
        # Sort by location (reverse order to maintain indices)
        sorted_issues = sorted(identity_issues, key=lambda i: i.location.start_index, reverse=True)
        
        for identity_issue in sorted_issues:
            replacement = self._generate_identity_claim_replacement(identity_issue, player)
            
            corrected_speech = (
                corrected_speech[:identity_issue.location.start_index] +
                replacement +
                corrected_speech[identity_issue.location.end_index:]
            )
        
        return corrected_speech
    
    def adjust_temporal_references(
        self, 
        speech: str, 
        temporal_errors: List[TemporalError]
    ) -> str:
        """
        Adjust temporal references to be contextually appropriate.
        
        Args:
            speech: Original speech
            temporal_errors: List of temporal errors to fix
            
        Returns:
            Speech with temporal references adjusted
        """
        corrected_speech = speech
        
        # Sort by location (reverse order to maintain indices)
        sorted_errors = sorted(temporal_errors, key=lambda e: e.location.start_index, reverse=True)
        
        for temporal_error in sorted_errors:
            replacement = self._generate_temporal_replacement(temporal_error)
            
            corrected_speech = (
                corrected_speech[:temporal_error.location.start_index] +
                replacement +
                corrected_speech[temporal_error.location.end_index:]
            )
        
        return corrected_speech
    
    def remove_fabricated_content(
        self, 
        speech: str, 
        fabrications: List[FabricatedInteraction]
    ) -> str:
        """
        Remove or replace fabricated interaction content.
        
        Args:
            speech: Original speech
            fabrications: List of fabricated interactions to fix
            
        Returns:
            Speech with fabricated content removed/replaced
        """
        corrected_speech = speech
        
        # Sort by location (reverse order to maintain indices)
        sorted_fabrications = sorted(fabrications, key=lambda f: f.location.start_index, reverse=True)
        
        for fabrication in sorted_fabrications:
            replacement = self._generate_interaction_replacement(fabrication)
            
            corrected_speech = (
                corrected_speech[:fabrication.location.start_index] +
                replacement +
                corrected_speech[fabrication.location.end_index:]
            )
        
        return corrected_speech
    
    def _correct_false_reference(
        self, 
        speech: str, 
        hallucination: Hallucination, 
        context: Dict[str, Any],
        player: Optional[Player]
    ) -> Tuple[str, Correction]:
        """Correct a false reference hallucination."""
        
        location = hallucination.location
        original_text = location.text
        
        # Generate generic replacement
        replacement = self._generate_generic_reference_from_hallucination(hallucination, context)
        
        # Apply correction
        corrected_speech = (
            speech[:location.start_index] +
            replacement +
            speech[location.end_index:]
        )
        
        correction = Correction(
            type=HallucinationType.FALSE_REFERENCE,
            original_text=original_text,
            corrected_text=replacement,
            reason="替换虚假引用为通用表述"
        )
        
        return corrected_speech, correction
    
    def _correct_identity_inconsistency(
        self, 
        speech: str, 
        hallucination: Hallucination, 
        context: Dict[str, Any],
        player: Optional[Player]
    ) -> Tuple[str, Correction]:
        """Correct an identity inconsistency hallucination."""
        
        location = hallucination.location
        original_text = location.text
        
        # Generate appropriate identity reference
        replacement = self._generate_identity_replacement_from_hallucination(hallucination, player)
        
        # Apply correction
        corrected_speech = (
            speech[:location.start_index] +
            replacement +
            speech[location.end_index:]
        )
        
        correction = Correction(
            type=HallucinationType.IDENTITY_INCONSISTENCY,
            original_text=original_text,
            corrected_text=replacement,
            reason="修正身份声明不一致"
        )
        
        return corrected_speech, correction
    
    def _correct_temporal_error(
        self, 
        speech: str, 
        hallucination: Hallucination, 
        context: Dict[str, Any],
        player: Optional[Player]
    ) -> Tuple[str, Correction]:
        """Correct a temporal error hallucination."""
        
        location = hallucination.location
        original_text = location.text
        
        # Generate appropriate temporal reference
        replacement = self._generate_temporal_replacement_from_hallucination(hallucination, context)
        
        # Apply correction
        corrected_speech = (
            speech[:location.start_index] +
            replacement +
            speech[location.end_index:]
        )
        
        correction = Correction(
            type=HallucinationType.TEMPORAL_ERROR,
            original_text=original_text,
            corrected_text=replacement,
            reason="修正时间引用错误"
        )
        
        return corrected_speech, correction
    
    def _correct_fabricated_interaction(
        self, 
        speech: str, 
        hallucination: Hallucination, 
        context: Dict[str, Any],
        player: Optional[Player]
    ) -> Tuple[str, Correction]:
        """Correct a fabricated interaction hallucination."""
        
        location = hallucination.location
        original_text = location.text
        
        # Generate generic interaction reference
        replacement = self._generate_generic_interaction_replacement(hallucination)
        
        # Apply correction
        corrected_speech = (
            speech[:location.start_index] +
            replacement +
            speech[location.end_index:]
        )
        
        correction = Correction(
            type=HallucinationType.FABRICATED_INTERACTION,
            original_text=original_text,
            corrected_text=replacement,
            reason="移除编造的互动内容"
        )
        
        return corrected_speech, correction
    
    def _generate_generic_reference_replacement(
        self, 
        false_ref: FalseReference, 
        context: Dict[str, Any]
    ) -> str:
        """Generate a generic replacement for a false reference."""
        
        speaker = false_ref.claimed_speaker
        
        # Generic replacement patterns
        generic_patterns = [
            f"{speaker}的观点",
            f"{speaker}的态度",
            f"{speaker}提到的内容",
            f"{speaker}的发言",
            f"根据{speaker}的表态",
        ]
        
        # Choose based on context or use the first one
        return generic_patterns[0]
    
    def _generate_identity_claim_replacement(
        self, 
        identity_issue: IdentityIssue, 
        player: Optional[Player]
    ) -> str:
        """Generate a replacement for identity claim issues."""
        
        player_name = identity_issue.player_mentioned
        
        if identity_issue.actual_identity:
            return f"{player_name}声称是{identity_issue.actual_identity}"
        else:
            return f"{player_name}的身份不明"
    
    def _generate_temporal_replacement(self, temporal_error: TemporalError) -> str:
        """Generate a replacement for temporal errors."""
        
        # Generic temporal replacements
        temporal_replacements = {
            "昨晚": "目前的情况",
            "前天": "之前",
            "上轮": "当前情况",
            "之前的": "现在的",
        }
        
        original = temporal_error.claimed_time_reference
        return temporal_replacements.get(original, "当前")
    
    def _generate_interaction_replacement(self, fabrication: FabricatedInteraction) -> str:
        """Generate a replacement for fabricated interactions."""
        
        players = "和".join(fabrication.involved_players)
        return f"基于{players}的公开发言"
    
    def _generate_generic_reference_from_hallucination(
        self, 
        hallucination: Hallucination, 
        context: Dict[str, Any]
    ) -> str:
        """Generate generic reference replacement from hallucination."""
        
        # Extract speaker name from description
        desc = hallucination.description
        speaker_match = re.search(r'：(\w+)从未', desc)
        
        if speaker_match:
            speaker = speaker_match.group(1)
            return f"{speaker}的相关表态"
        
        return "相关的发言内容"
    
    def _generate_identity_replacement_from_hallucination(
        self, 
        hallucination: Hallucination, 
        player: Optional[Player]
    ) -> str:
        """Generate identity replacement from hallucination."""
        
        # Extract player name from description
        desc = hallucination.description
        player_match = re.search(r'：(\w+)从未', desc)
        
        if player_match:
            player_name = player_match.group(1)
            return f"{player_name}的身份表态"
        
        return "相关玩家的身份"
    
    def _generate_temporal_replacement_from_hallucination(
        self, 
        hallucination: Hallucination, 
        context: Dict[str, Any]
    ) -> str:
        """Generate temporal replacement from hallucination."""
        
        current_round = context.get("current_round", 1)
        
        if current_round == 1:
            return "当前的情况"
        else:
            return "目前的状况"
    
    def _generate_generic_interaction_replacement(self, hallucination: Hallucination) -> str:
        """Generate generic interaction replacement from hallucination."""
        
        return "基于公开信息的分析"
    
    def _evaluate_correction_quality(
        self, 
        original: str, 
        corrected: str, 
        corrections: List[Correction]
    ) -> float:
        """
        Evaluate the quality of the correction.
        
        Args:
            original: Original speech
            corrected: Corrected speech
            corrections: List of applied corrections
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not corrections:
            return 1.0 if original == corrected else 0.0
        
        # Base quality score
        quality_score = 0.8
        
        # Penalize if corrected speech is too different in length
        length_ratio = len(corrected) / max(len(original), 1)
        if length_ratio < 0.5 or length_ratio > 1.5:
            quality_score -= 0.2
        
        # Bonus for maintaining sentence structure
        original_sentences = len(re.findall(r'[。！？]', original))
        corrected_sentences = len(re.findall(r'[。！？]', corrected))
        
        if abs(original_sentences - corrected_sentences) <= 1:
            quality_score += 0.1
        
        # Ensure score is within bounds
        return max(0.0, min(1.0, quality_score))