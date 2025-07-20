"""
Multi-layer hallucination detection system for werewolf game LLM players.
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
    TextLocation,
    HallucinationDetectionError,
    HallucinationReductionConfig
)
from ..models.player import Player
from .speech_history_tracker import SpeechHistoryTracker


class MultiLayerHallucinationDetector:
    """
    Multi-layer hallucination detection system that identifies different types
    of hallucinations in LLM player speeches.
    """
    
    def __init__(self, config: Optional[HallucinationReductionConfig] = None):
        """
        Initialize the hallucination detector.
        
        Args:
            config: Configuration for hallucination detection
        """
        self.config = config or HallucinationReductionConfig()
        self._detection_layers = [
            self._detect_false_references_layer,
            self._detect_identity_inconsistencies_layer,
            self._detect_temporal_errors_layer,
            self._detect_fabricated_interactions_layer
        ]
    
    def detect_all_hallucinations(
        self, 
        speech: str, 
        player: Player, 
        context: Dict[str, Any],
        speech_tracker: SpeechHistoryTracker
    ) -> HallucinationResult:
        """
        Detect all types of hallucinations in a player's speech.
        
        Args:
            speech: The speech content to analyze
            player: The player who made the speech
            context: Game context information
            speech_tracker: Speech history tracker for reference verification
            
        Returns:
            HallucinationResult with detected hallucinations
        """
        try:
            all_hallucinations = []
            detection_start_time = datetime.now()
            
            # Run each detection layer
            for layer_func in self._detection_layers:
                try:
                    layer_hallucinations = layer_func(speech, player, context, speech_tracker)
                    all_hallucinations.extend(layer_hallucinations)
                except Exception as e:
                    print(f"Warning: Detection layer failed: {e}")
                    continue
            
            # Check detection time limit
            detection_time = (datetime.now() - detection_start_time).total_seconds()
            if detection_time > self.config.max_detection_time:
                print(f"Warning: Detection took {detection_time:.2f}s, exceeding limit of {self.config.max_detection_time}s")
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(all_hallucinations, speech)
            
            # Determine if correction is needed
            correction_needed = (
                len(all_hallucinations) > 0 and 
                self.config.enable_auto_correction and
                confidence_score >= self.config.detection_strictness
            )
            
            return HallucinationResult(
                is_valid=len(all_hallucinations) == 0,
                hallucination_count=len(all_hallucinations),
                hallucinations=all_hallucinations,
                confidence_score=confidence_score,
                correction_needed=correction_needed
            )
            
        except Exception as e:
            raise HallucinationDetectionError(
                f"Failed to detect hallucinations: {str(e)}",
                player_id=player.id,
                speech=speech
            )
    
    def detect_false_references(
        self, 
        speech: str, 
        context: Dict[str, Any],
        speech_tracker: SpeechHistoryTracker
    ) -> List[FalseReference]:
        """
        Detect false references to other players' speeches.
        
        Args:
            speech: Speech content to analyze
            context: Game context
            speech_tracker: Speech history tracker
            
        Returns:
            List of detected false references
        """
        return self._detect_false_references_layer(speech, None, context, speech_tracker)
    
    def detect_identity_inconsistencies(
        self, 
        speech: str, 
        player: Player,
        speech_tracker: SpeechHistoryTracker
    ) -> List[IdentityIssue]:
        """
        Detect identity-related inconsistencies.
        
        Args:
            speech: Speech content to analyze
            player: The speaking player
            speech_tracker: Speech history tracker
            
        Returns:
            List of detected identity issues
        """
        return self._detect_identity_inconsistencies_layer(speech, player, {}, speech_tracker)
    
    def detect_temporal_errors(
        self, 
        speech: str, 
        round_num: int
    ) -> List[TemporalError]:
        """
        Detect temporal reference errors.
        
        Args:
            speech: Speech content to analyze
            round_num: Current round number
            
        Returns:
            List of detected temporal errors
        """
        context = {"current_round": round_num}
        return self._detect_temporal_errors_layer(speech, None, context, None)
    
    def detect_fabricated_interactions(
        self, 
        speech: str, 
        context: Dict[str, Any],
        speech_tracker: SpeechHistoryTracker
    ) -> List[FabricatedInteraction]:
        """
        Detect fabricated interactions between players.
        
        Args:
            speech: Speech content to analyze
            context: Game context
            speech_tracker: Speech history tracker
            
        Returns:
            List of detected fabricated interactions
        """
        return self._detect_fabricated_interactions_layer(speech, None, context, speech_tracker)
    
    def _detect_false_references_layer(
        self, 
        speech: str, 
        player: Optional[Player], 
        context: Dict[str, Any],
        speech_tracker: SpeechHistoryTracker
    ) -> List[Hallucination]:
        """Detect false references to other players' speeches with enhanced accuracy."""
        hallucinations = []
        
        try:
            # Enhanced patterns to detect speech references in Chinese
            reference_patterns = [
                # Direct quotes
                (r'(\w+)说[过了]?"([^"]{3,})"', 2, "direct_quote"),
                (r'(\w+)说[过了]?：["""]([^"""]{3,})["""]', 2, "direct_quote"),
                
                # Indirect references
                (r'(\w+)说[过了]?(.{5,30})', 2, "indirect_reference"),
                (r'根据(\w+)的话[，,](.{5,30})', 2, "based_on_speech"),
                (r'(\w+)提到[过了]?(.{5,30})', 2, "mentioned"),
                (r'(\w+)声称(.{5,30})', 2, "claimed"),
                (r'(\w+)表示(.{5,30})', 2, "expressed"),
                (r'(\w+)认为(.{5,30})', 2, "thinks"),
                
                # Specific game-related references
                (r'(\w+)说[过了]?自己是(\w+)', 2, "identity_claim"),
                (r'(\w+)跳[了]?(\w+)', 2, "role_jump"),
                (r'(\w+)查验[了]?(\w+)', 2, "seer_check"),
                (r'(\w+)怀疑(\w+)', 2, "suspicion"),
            ]
            
            for pattern, content_group, ref_type in reference_patterns:
                matches = re.finditer(pattern, speech, re.IGNORECASE)
                
                for match in matches:
                    claimed_speaker = match.group(1)
                    claimed_content = match.group(content_group).strip('，。！？；：""''（）【】')
                    
                    # Skip very short or generic content
                    if len(claimed_content.strip()) < 3:
                        continue
                    
                    # Find player by name
                    speaker_id = self._find_player_id_by_name(claimed_speaker, context)
                    if speaker_id is None:
                        continue
                    
                    # Enhanced verification with different strategies based on reference type
                    is_valid, verification_details = self._enhanced_reference_verification(
                        claimed_content, speaker_id, ref_type, speech_tracker
                    )
                    
                    if not is_valid:
                        location = TextLocation(
                            start_index=match.start(),
                            end_index=match.end(),
                            text=match.group(0)
                        )
                        
                        false_ref = FalseReference(
                            claimed_speaker=claimed_speaker,
                            claimed_content=claimed_content,
                            actual_content=verification_details.get("best_match_content"),
                            location=location
                        )
                        
                        severity = self._determine_enhanced_severity(
                            verification_details.get("similarity", 0.0), 
                            claimed_content, 
                            ref_type
                        )
                        
                        hallucination = Hallucination(
                            type=HallucinationType.FALSE_REFERENCE,
                            description=self._generate_false_reference_description(
                                claimed_speaker, claimed_content, ref_type, verification_details
                            ),
                            location=location,
                            severity=severity,
                            suggested_correction=self._suggest_enhanced_false_reference_correction(
                                false_ref, verification_details, ref_type
                            )
                        )
                        
                        hallucinations.append(hallucination)
            
        except Exception as e:
            print(f"Error in enhanced false reference detection: {e}")
        
        return hallucinations
    
    def _enhanced_reference_verification(
        self, 
        claimed_content: str, 
        speaker_id: int, 
        ref_type: str,
        speech_tracker: SpeechHistoryTracker
    ) -> Tuple[bool, Dict[str, Any]]:
        """Enhanced verification of speech references with detailed analysis."""
        verification_details = {
            "similarity": 0.0,
            "best_match_content": None,
            "verification_method": ref_type,
            "exact_match": False,
            "partial_match": False,
            "semantic_match": False
        }
        
        try:
            # Get all speeches by the claimed speaker
            player_speeches = speech_tracker.get_player_speeches(speaker_id)
            
            if not player_speeches:
                return False, verification_details
            
            best_similarity = 0.0
            best_match = None
            
            for speech_record in player_speeches:
                actual_content = speech_record.speech_content
                
                # Exact match check
                if self._exact_content_match(claimed_content, actual_content):
                    verification_details.update({
                        "exact_match": True,
                        "best_match_content": actual_content,
                        "similarity": 1.0
                    })
                    return True, verification_details
                
                # Partial match check
                if self._partial_content_match(claimed_content, actual_content):
                    verification_details["partial_match"] = True
                
                # Semantic similarity check
                similarity = self._calculate_semantic_similarity(claimed_content, actual_content, ref_type)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = actual_content
            
            verification_details.update({
                "similarity": best_similarity,
                "best_match_content": best_match,
                "semantic_match": best_similarity > 0.6
            })
            
            # Determine validity based on reference type and similarity
            is_valid = self._determine_reference_validity(best_similarity, ref_type, verification_details)
            
            return is_valid, verification_details
            
        except Exception as e:
            print(f"Error in enhanced reference verification: {e}")
            return False, verification_details
    
    def _exact_content_match(self, claimed: str, actual: str) -> bool:
        """Check for exact content match with normalization."""
        claimed_norm = re.sub(r'[，。！？；：""''（）【】\s]', '', claimed.lower())
        actual_norm = re.sub(r'[，。！？；：""''（）【】\s]', '', actual.lower())
        return claimed_norm == actual_norm
    
    def _partial_content_match(self, claimed: str, actual: str) -> bool:
        """Check for meaningful partial content match."""
        claimed_norm = re.sub(r'[，。！？；：""''（）【】]', '', claimed.lower())
        actual_norm = re.sub(r'[，。！？；：""''（）【】]', '', actual.lower())
        
        # Check if claimed is a substantial substring of actual or vice versa
        min_length = min(len(claimed_norm), len(actual_norm))
        if min_length < 5:  # Too short to be meaningful
            return False
        
        return (claimed_norm in actual_norm and len(claimed_norm) / len(actual_norm) > 0.3) or \
               (actual_norm in claimed_norm and len(actual_norm) / len(claimed_norm) > 0.3)
    
    def _calculate_semantic_similarity(self, claimed: str, actual: str, ref_type: str) -> float:
        """Calculate semantic similarity based on reference type."""
        from difflib import SequenceMatcher
        
        # Basic sequence matching
        base_similarity = SequenceMatcher(None, claimed.lower(), actual.lower()).ratio()
        
        # Adjust based on reference type
        if ref_type == "identity_claim":
            # For identity claims, look for role keywords
            identity_keywords = ["预言家", "村民", "女巫", "猎人", "狼人"]
            claimed_roles = [kw for kw in identity_keywords if kw in claimed]
            actual_roles = [kw for kw in identity_keywords if kw in actual]
            
            if claimed_roles and actual_roles:
                role_match = len(set(claimed_roles) & set(actual_roles)) / len(set(claimed_roles) | set(actual_roles))
                base_similarity = max(base_similarity, role_match)
        
        elif ref_type == "suspicion":
            # For suspicion, look for negative sentiment keywords
            suspicion_keywords = ["可疑", "怀疑", "不信任", "狼人", "撒谎"]
            claimed_suspicion = any(kw in claimed for kw in suspicion_keywords)
            actual_suspicion = any(kw in actual for kw in suspicion_keywords)
            
            if claimed_suspicion == actual_suspicion:
                base_similarity += 0.2
        
        return min(base_similarity, 1.0)
    
    def _determine_reference_validity(
        self, 
        similarity: float, 
        ref_type: str, 
        verification_details: Dict[str, Any]
    ) -> bool:
        """Determine if a reference is valid based on similarity and type."""
        
        # Exact or partial matches are always valid
        if verification_details.get("exact_match") or verification_details.get("partial_match"):
            return True
        
        # Different thresholds for different reference types
        thresholds = {
            "direct_quote": 0.8,      # Direct quotes need high similarity
            "identity_claim": 0.7,    # Identity claims need good similarity
            "indirect_reference": 0.6, # Indirect references are more flexible
            "mentioned": 0.5,         # Mentions can be more general
            "thinks": 0.4,           # Thoughts/opinions can be paraphrased
        }
        
        threshold = thresholds.get(ref_type, 0.6)
        return similarity >= threshold
    
    def _determine_enhanced_severity(self, similarity: float, claimed_content: str, ref_type: str) -> HallucinationSeverity:
        """Determine hallucination severity with enhanced logic."""
        
        # Direct quotes with low similarity are critical
        if ref_type == "direct_quote" and similarity < 0.3:
            return HallucinationSeverity.CRITICAL
        
        # Identity claims are always high severity if false
        if ref_type == "identity_claim":
            return HallucinationSeverity.HIGH
        
        # Long false claims are more severe
        if len(claimed_content) > 30 and similarity < 0.2:
            return HallucinationSeverity.HIGH
        
        # Medium similarity suggests misremembering rather than fabrication
        if similarity > 0.4:
            return HallucinationSeverity.LOW
        elif similarity > 0.2:
            return HallucinationSeverity.MEDIUM
        else:
            return HallucinationSeverity.HIGH
    
    def _generate_false_reference_description(
        self, 
        speaker: str, 
        content: str, 
        ref_type: str, 
        verification_details: Dict[str, Any]
    ) -> str:
        """Generate detailed description for false reference."""
        
        base_desc = f"虚假引用：{speaker}从未"
        
        if ref_type == "direct_quote":
            base_desc += f'说过"{content}"'
        elif ref_type == "identity_claim":
            base_desc += f"声称自己是{content}"
        elif ref_type == "suspicion":
            base_desc += f"表达过对{content}的怀疑"
        else:
            base_desc += f"提及过'{content}'"
        
        # Add similarity information if available
        similarity = verification_details.get("similarity", 0.0)
        if similarity > 0.3:
            base_desc += f"（相似度：{similarity:.1%}，可能是记忆偏差）"
        
        return base_desc
    
    def _suggest_enhanced_false_reference_correction(
        self, 
        false_ref: FalseReference, 
        verification_details: Dict[str, Any], 
        ref_type: str
    ) -> str:
        """Generate enhanced correction suggestions."""
        
        speaker = false_ref.claimed_speaker
        similarity = verification_details.get("similarity", 0.0)
        best_match = verification_details.get("best_match_content")
        
        if similarity > 0.6 and best_match:
            return f"可以说'{speaker}提到了相关内容'，但避免具体引用"
        elif ref_type == "identity_claim":
            return f"避免声称{speaker}的具体身份，可以说'身份不明'或'未明确表态'"
        elif ref_type == "direct_quote":
            return f"避免直接引用{speaker}的话，可以用'大意是'或'类似表达'"
        else:
            return f"用更通用的表述，如'{speaker}的观点'或'{speaker}的态度'"
    
    def _detect_identity_inconsistencies_layer(
        self, 
        speech: str, 
        player: Optional[Player], 
        context: Dict[str, Any],
        speech_tracker: SpeechHistoryTracker
    ) -> List[Hallucination]:
        """Detect identity-related inconsistencies."""
        hallucinations = []
        
        try:
            # Patterns to detect identity claims about others
            identity_patterns = [
                r'(\w+)说[过了]?自己是(\w+)',      # X说自己是预言家
                r'(\w+)是(\w+)',                  # X是预言家
                r'(\w+)声称[自己]?是(\w+)',        # X声称是预言家
                r'(\w+)跳[了]?(\w+)',             # X跳预言家
            ]
            
            for pattern in identity_patterns:
                matches = re.finditer(pattern, speech, re.IGNORECASE)
                
                for match in matches:
                    claimed_player = match.group(1)
                    claimed_identity = match.group(2)
                    
                    # Find player by name
                    player_id = self._find_player_id_by_name(claimed_player, context)
                    if player_id is None:
                        continue
                    
                    # Verify the identity claim
                    is_valid = speech_tracker.verify_identity_claim_reference(claimed_identity, player_id)
                    
                    if not is_valid:
                        location = TextLocation(
                            start_index=match.start(),
                            end_index=match.end(),
                            text=match.group(0)
                        )
                        
                        # Get actual identity claims
                        actual_claims = speech_tracker.get_player_identity_claims(player_id)
                        
                        identity_issue = IdentityIssue(
                            player_mentioned=claimed_player,
                            claimed_identity=claimed_identity,
                            actual_identity=actual_claims[0] if actual_claims else None,
                            location=location
                        )
                        
                        hallucination = Hallucination(
                            type=HallucinationType.IDENTITY_INCONSISTENCY,
                            description=f"身份声明不一致：{claimed_player}从未声称自己是{claimed_identity}",
                            location=location,
                            severity=HallucinationSeverity.HIGH,
                            suggested_correction=self._suggest_identity_correction(identity_issue)
                        )
                        
                        hallucinations.append(hallucination)
            
        except Exception as e:
            print(f"Error in identity inconsistency detection: {e}")
        
        return hallucinations
    
    def _detect_temporal_errors_layer(
        self, 
        speech: str, 
        player: Optional[Player], 
        context: Dict[str, Any],
        speech_tracker: Optional[SpeechHistoryTracker]
    ) -> List[Hallucination]:
        """Detect temporal reference errors."""
        hallucinations = []
        
        try:
            current_round = context.get("current_round", 1)
            
            # Patterns for temporal references
            temporal_patterns = [
                r'昨晚',
                r'前[几]?天',
                r'之前的[轮回合]',
                r'上[一]?轮',
                r'第[一二三四五六七八九十\d]+[轮回合天]',
            ]
            
            for pattern in temporal_patterns:
                matches = re.finditer(pattern, speech, re.IGNORECASE)
                
                for match in matches:
                    temporal_ref = match.group(0)
                    
                    # Check if temporal reference is valid for current round
                    is_valid = self._validate_temporal_reference(temporal_ref, current_round)
                    
                    if not is_valid:
                        location = TextLocation(
                            start_index=match.start(),
                            end_index=match.end(),
                            text=temporal_ref
                        )
                        
                        temporal_error = TemporalError(
                            claimed_time_reference=temporal_ref,
                            actual_time_context=f"当前是第{current_round}轮",
                            location=location
                        )
                        
                        hallucination = Hallucination(
                            type=HallucinationType.TEMPORAL_ERROR,
                            description=f"时间引用错误：在第{current_round}轮提及'{temporal_ref}'",
                            location=location,
                            severity=HallucinationSeverity.MEDIUM,
                            suggested_correction=self._suggest_temporal_correction(temporal_error, current_round)
                        )
                        
                        hallucinations.append(hallucination)
            
        except Exception as e:
            print(f"Error in temporal error detection: {e}")
        
        return hallucinations
    
    def _detect_fabricated_interactions_layer(
        self, 
        speech: str, 
        player: Optional[Player], 
        context: Dict[str, Any],
        speech_tracker: SpeechHistoryTracker
    ) -> List[Hallucination]:
        """Detect fabricated interactions between players."""
        hallucinations = []
        
        try:
            # Patterns for player interactions
            interaction_patterns = [
                r'(\w+)和(\w+)[一起共同](.{1,30})',     # X和Y一起...
                r'(\w+)支持[了]?(\w+)',               # X支持Y
                r'(\w+)反对[了]?(\w+)',               # X反对Y
                r'(\w+)质疑[了]?(\w+)',               # X质疑Y
            ]
            
            for pattern in interaction_patterns:
                matches = re.finditer(pattern, speech, re.IGNORECASE)
                
                for match in matches:
                    if len(match.groups()) >= 2:
                        player1 = match.group(1)
                        player2 = match.group(2)
                        interaction = match.group(3) if len(match.groups()) > 2 else match.group(0)
                        
                        # Verify if this interaction actually occurred
                        is_valid = self._verify_player_interaction(player1, player2, interaction, speech_tracker)
                        
                        if not is_valid:
                            location = TextLocation(
                                start_index=match.start(),
                                end_index=match.end(),
                                text=match.group(0)
                            )
                            
                            fabricated_interaction = FabricatedInteraction(
                                involved_players=[player1, player2],
                                claimed_interaction=interaction,
                                location=location
                            )
                            
                            hallucination = Hallucination(
                                type=HallucinationType.FABRICATED_INTERACTION,
                                description=f"编造的互动：{player1}和{player2}之间的'{interaction}'互动未发生",
                                location=location,
                                severity=HallucinationSeverity.MEDIUM,
                                suggested_correction=self._suggest_interaction_correction(fabricated_interaction)
                            )
                            
                            hallucinations.append(hallucination)
            
        except Exception as e:
            print(f"Error in fabricated interaction detection: {e}")
        
        return hallucinations
    
    def _find_player_id_by_name(self, name: str, context: Dict[str, Any]) -> Optional[int]:
        """Find player ID by name from context."""
        all_players = context.get("all_players", [])
        for player_info in all_players:
            if player_info.get("name") == name:
                return player_info.get("id")
        return None
    
    def _determine_severity(self, similarity: float, claimed_content: str) -> HallucinationSeverity:
        """Determine hallucination severity based on similarity and content."""
        if similarity > 0.7:
            return HallucinationSeverity.LOW
        elif similarity > 0.4:
            return HallucinationSeverity.MEDIUM
        elif len(claimed_content) > 20:
            return HallucinationSeverity.HIGH
        else:
            return HallucinationSeverity.CRITICAL
    
    def _validate_temporal_reference(self, temporal_ref: str, current_round: int) -> bool:
        """Validate if a temporal reference is appropriate for the current round."""
        if current_round == 1:
            # First round - no previous events
            invalid_first_round = ["昨晚", "前天", "之前的", "上轮"]
            return not any(invalid in temporal_ref for invalid in invalid_first_round)
        
        # For later rounds, most temporal references are valid
        return True
    
    def _verify_player_interaction(
        self, 
        player1: str, 
        player2: str, 
        interaction: str,
        speech_tracker: SpeechHistoryTracker
    ) -> bool:
        """Verify if a claimed player interaction actually occurred."""
        # This is a simplified verification - could be enhanced with more sophisticated analysis
        # For now, we assume most interactions are valid unless they're very specific claims
        specific_claims = ["一起投票", "私下交流", "达成协议"]
        return not any(claim in interaction for claim in specific_claims)
    
    def _calculate_confidence_score(self, hallucinations: List[Hallucination], speech: str) -> float:
        """Calculate confidence score for the detection results."""
        if not hallucinations:
            return 1.0
        
        # Weight by severity
        severity_weights = {
            HallucinationSeverity.LOW: 0.2,
            HallucinationSeverity.MEDIUM: 0.5,
            HallucinationSeverity.HIGH: 0.8,
            HallucinationSeverity.CRITICAL: 1.0
        }
        
        total_weight = sum(severity_weights[h.severity] for h in hallucinations)
        speech_length = len(speech)
        
        # Normalize by speech length
        confidence = min(total_weight / max(speech_length / 100, 1), 1.0)
        
        return max(1.0 - confidence, 0.0)
    
    def _suggest_false_reference_correction(
        self, 
        false_ref: FalseReference, 
        best_match: Optional[Any]
    ) -> str:
        """Suggest correction for false reference."""
        if best_match and best_match.speech_content:
            return f"可以说'{false_ref.claimed_speaker}提到了相关内容'而不是具体引用"
        else:
            return f"避免引用{false_ref.claimed_speaker}的具体发言，可以用通用表述"
    
    def _suggest_identity_correction(self, identity_issue: IdentityIssue) -> str:
        """Suggest correction for identity inconsistency."""
        if identity_issue.actual_identity:
            return f"可以说'{identity_issue.player_mentioned}声称是{identity_issue.actual_identity}'"
        else:
            return f"避免声称{identity_issue.player_mentioned}的具体身份，可以说'身份不明'"
    
    def _suggest_temporal_correction(self, temporal_error: TemporalError, current_round: int) -> str:
        """Suggest correction for temporal error."""
        if current_round == 1:
            return "第一轮游戏，避免引用前夜或历史事件"
        else:
            return f"当前是第{current_round}轮，请确认时间引用的准确性"
    
    def _suggest_interaction_correction(self, fabricated_interaction: FabricatedInteraction) -> str:
        """Suggest correction for fabricated interaction."""
        players = "和".join(fabricated_interaction.involved_players)
        return f"避免声称{players}之间的具体互动，可以基于公开发言进行分析"