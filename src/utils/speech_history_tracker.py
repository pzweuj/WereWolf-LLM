"""
Speech History Tracker for maintaining accurate speech records in the werewolf game.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from ..models.hallucination_models import (
    SpeechRecord,
    ReferenceInfo,
    SpeechHistoryError
)


class SpeechHistoryTracker:
    """
    Tracks and manages speech history for all players in the game.
    Provides functionality for recording, retrieving, and validating speech references.
    """
    
    def __init__(self, max_history_length: int = 100):
        """
        Initialize the speech history tracker.
        
        Args:
            max_history_length: Maximum number of speech records to maintain
        """
        self.max_history_length = max_history_length
        self._speech_records: List[SpeechRecord] = []
        self._player_speech_index: Dict[int, List[int]] = {}  # player_id -> list of record indices
        self._round_speech_index: Dict[int, List[int]] = {}  # round_number -> list of record indices
        self._phase_speech_index: Dict[str, List[int]] = {}  # phase -> list of record indices
        
    def record_speech(
        self, 
        player_id: int, 
        player_name: str,
        speech: str, 
        round_num: int, 
        phase: str,
        speaking_order: int = 0
    ) -> bool:
        """
        Record a player's speech in the game.
        
        Args:
            player_id: ID of the speaking player
            player_name: Name of the speaking player
            speech: Content of the speech
            round_num: Current round number
            phase: Current game phase
            speaking_order: Order of speaking in the current phase
            
        Returns:
            bool: True if recording was successful
            
        Raises:
            SpeechHistoryError: If recording fails
        """
        try:
            # Create speech record
            speech_record = SpeechRecord(
                player_id=player_id,
                player_name=player_name,
                speech_content=speech,
                round_number=round_num,
                phase=phase,
                timestamp=datetime.now(),
                speaking_order=speaking_order
            )
            
            # Add to main records list
            record_index = len(self._speech_records)
            self._speech_records.append(speech_record)
            
            # Update indices
            self._update_player_index(player_id, record_index)
            self._update_round_index(round_num, record_index)
            self._update_phase_index(phase, record_index)
            
            # Maintain max history length
            self._cleanup_old_records()
            
            return True
            
        except Exception as e:
            raise SpeechHistoryError(
                f"Failed to record speech for player {player_id}: {str(e)}",
                player_id=player_id,
                round_number=round_num
            )
    
    def get_player_speeches(
        self, 
        player_id: int, 
        round_num: Optional[int] = None,
        phase: Optional[str] = None
    ) -> List[SpeechRecord]:
        """
        Get all speeches by a specific player.
        
        Args:
            player_id: ID of the player
            round_num: Optional filter by round number
            phase: Optional filter by phase
            
        Returns:
            List of speech records for the player
        """
        try:
            if player_id not in self._player_speech_index:
                return []
            
            player_indices = self._player_speech_index[player_id]
            speeches = [self._speech_records[i] for i in player_indices if i < len(self._speech_records)]
            
            # Apply filters
            if round_num is not None:
                speeches = [s for s in speeches if s.round_number == round_num]
            
            if phase is not None:
                speeches = [s for s in speeches if s.phase == phase]
            
            return sorted(speeches, key=lambda x: (x.round_number, x.speaking_order))
            
        except Exception as e:
            raise SpeechHistoryError(
                f"Failed to get speeches for player {player_id}: {str(e)}",
                player_id=player_id,
                round_number=round_num
            )
    
    def get_round_speeches(
        self, 
        round_num: int, 
        phase: Optional[str] = None
    ) -> List[SpeechRecord]:
        """
        Get all speeches from a specific round.
        
        Args:
            round_num: Round number to retrieve
            phase: Optional filter by phase
            
        Returns:
            List of speech records from the round
        """
        try:
            if round_num not in self._round_speech_index:
                return []
            
            round_indices = self._round_speech_index[round_num]
            speeches = [self._speech_records[i] for i in round_indices if i < len(self._speech_records)]
            
            # Apply phase filter
            if phase is not None:
                speeches = [s for s in speeches if s.phase == phase]
            
            return sorted(speeches, key=lambda x: x.speaking_order)
            
        except Exception as e:
            raise SpeechHistoryError(
                f"Failed to get speeches for round {round_num}: {str(e)}",
                round_number=round_num
            )
    
    def get_all_speeches(
        self, 
        limit: Optional[int] = None
    ) -> List[SpeechRecord]:
        """
        Get all speech records.
        
        Args:
            limit: Optional limit on number of records to return
            
        Returns:
            List of all speech records
        """
        speeches = sorted(
            self._speech_records, 
            key=lambda x: (x.round_number, x.speaking_order)
        )
        
        if limit is not None:
            speeches = speeches[-limit:]
        
        return speeches
    
    def verify_speech_reference(
        self, 
        claimed_speech: str, 
        claimed_speaker_id: int,
        similarity_threshold: float = 0.7,
        use_fuzzy_matching: bool = True
    ) -> bool:
        """
        Verify if a claimed speech reference actually exists.
        
        Args:
            claimed_speech: The speech content being claimed
            claimed_speaker_id: ID of the claimed speaker
            similarity_threshold: Minimum similarity score for match
            use_fuzzy_matching: Whether to use fuzzy matching algorithm
            
        Returns:
            bool: True if the reference is valid
        """
        try:
            player_speeches = self.get_player_speeches(claimed_speaker_id)
            
            if not player_speeches:
                return False
            
            # Clean and normalize the claimed speech
            claimed_speech_clean = self._normalize_text(claimed_speech)
            
            for speech_record in player_speeches:
                actual_speech_clean = self._normalize_text(speech_record.speech_content)
                
                # Try exact match first
                if self._exact_match(claimed_speech_clean, actual_speech_clean):
                    return True
                
                # Try substring match
                if self._substring_match(claimed_speech_clean, actual_speech_clean):
                    return True
                
                # Try fuzzy matching if enabled
                if use_fuzzy_matching:
                    similarity = self._calculate_similarity(claimed_speech_clean, actual_speech_clean)
                    if similarity >= similarity_threshold:
                        return True
            
            return False
            
        except Exception as e:
            raise SpeechHistoryError(
                f"Failed to verify speech reference: {str(e)}",
                player_id=claimed_speaker_id
            )
    
    def find_best_speech_match(
        self, 
        claimed_speech: str, 
        claimed_speaker_id: int,
        min_similarity: float = 0.5
    ) -> Tuple[Optional[SpeechRecord], float]:
        """
        Find the best matching speech record for a claimed reference.
        
        Args:
            claimed_speech: The speech content being claimed
            claimed_speaker_id: ID of the claimed speaker
            min_similarity: Minimum similarity threshold
            
        Returns:
            Tuple of (best_match_record, similarity_score)
        """
        try:
            player_speeches = self.get_player_speeches(claimed_speaker_id)
            
            if not player_speeches:
                return None, 0.0
            
            claimed_speech_clean = self._normalize_text(claimed_speech)
            best_match = None
            best_similarity = 0.0
            
            for speech_record in player_speeches:
                actual_speech_clean = self._normalize_text(speech_record.speech_content)
                similarity = self._calculate_similarity(claimed_speech_clean, actual_speech_clean)
                
                if similarity > best_similarity and similarity >= min_similarity:
                    best_similarity = similarity
                    best_match = speech_record
            
            return best_match, best_similarity
            
        except Exception as e:
            raise SpeechHistoryError(
                f"Failed to find best speech match: {str(e)}",
                player_id=claimed_speaker_id
            )
    
    def verify_identity_claim_reference(
        self, 
        claimed_identity: str, 
        claimed_speaker_id: int
    ) -> bool:
        """
        Verify if a player actually claimed a specific identity.
        
        Args:
            claimed_identity: The identity being claimed (e.g., "预言家", "村民")
            claimed_speaker_id: ID of the player who supposedly made the claim
            
        Returns:
            bool: True if the identity claim reference is valid
        """
        try:
            player_speeches = self.get_player_speeches(claimed_speaker_id)
            
            # Common identity claim patterns in Chinese
            identity_patterns = {
                "预言家": [r"我是预言家", r"我.*预言家", r"预言家.*我"],
                "村民": [r"我是村民", r"我.*村民", r"村民.*我"],
                "女巫": [r"我是女巫", r"我.*女巫", r"女巫.*我"],
                "猎人": [r"我是猎人", r"我.*猎人", r"猎人.*我"],
                "狼人": [r"我是狼人", r"我.*狼人", r"狼人.*我"],
            }
            
            patterns = identity_patterns.get(claimed_identity, [claimed_identity])
            
            for speech_record in player_speeches:
                speech_content = speech_record.speech_content
                
                # Check each pattern
                for pattern in patterns:
                    if re.search(pattern, speech_content, re.IGNORECASE):
                        return True
            
            return False
            
        except Exception as e:
            raise SpeechHistoryError(
                f"Failed to verify identity claim reference: {str(e)}",
                player_id=claimed_speaker_id
            )
    
    def get_player_identity_claims(self, player_id: int) -> List[str]:
        """
        Get all identity claims made by a specific player.
        
        Args:
            player_id: ID of the player
            
        Returns:
            List of identity claims found in the player's speeches
        """
        try:
            player_speeches = self.get_player_speeches(player_id)
            identity_claims = []
            
            # Identity patterns to search for
            identity_patterns = {
                "预言家": [r"我是预言家", r"我.*预言家"],
                "村民": [r"我是村民", r"我.*村民"],
                "女巫": [r"我是女巫", r"我.*女巫"],
                "猎人": [r"我是猎人", r"我.*猎人"],
                "狼人": [r"我是狼人", r"我.*狼人"],
            }
            
            for speech_record in player_speeches:
                speech_content = speech_record.speech_content
                
                for identity, patterns in identity_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, speech_content, re.IGNORECASE):
                            if identity not in identity_claims:
                                identity_claims.append(identity)
                            break
            
            return identity_claims
            
        except Exception as e:
            raise SpeechHistoryError(
                f"Failed to get player identity claims: {str(e)}",
                player_id=player_id
            )
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison by removing extra whitespace and punctuation.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common punctuation (but keep Chinese punctuation context)
        text = re.sub(r'[，。！？；：""''（）【】]', '', text)
        
        return text.lower()
    
    def _exact_match(self, text1: str, text2: str) -> bool:
        """Check for exact match between two normalized texts."""
        return text1 == text2
    
    def _substring_match(self, claimed: str, actual: str) -> bool:
        """
        Check for substring match in both directions.
        
        Args:
            claimed: Claimed speech text
            actual: Actual speech text
            
        Returns:
            bool: True if there's a meaningful substring match
        """
        # Avoid matching very short strings
        min_length = 3
        
        if len(claimed) < min_length or len(actual) < min_length:
            return False
        
        # Check if claimed is substring of actual or vice versa
        return claimed in actual or actual in claimed
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using sequence matching.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for similarity calculation
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    def get_available_references(
        self, 
        current_round: int, 
        current_phase: str,
        exclude_player_id: Optional[int] = None
    ) -> List[ReferenceInfo]:
        """
        Get list of available speech references that can be cited.
        
        Args:
            current_round: Current round number
            current_phase: Current game phase
            exclude_player_id: Optional player ID to exclude from references
            
        Returns:
            List of available reference information
        """
        try:
            available_refs = []
            
            # Get speeches from previous rounds and current round up to current phase
            for speech_record in self._speech_records:
                # Skip if this is the excluded player
                if exclude_player_id and speech_record.player_id == exclude_player_id:
                    continue
                
                # Include speeches from previous rounds
                if speech_record.round_number < current_round:
                    is_available = True
                # Include speeches from current round in previous phases or same phase
                elif speech_record.round_number == current_round:
                    # This logic can be enhanced based on phase ordering
                    is_available = True
                else:
                    is_available = False
                
                ref_info = ReferenceInfo(
                    player_id=speech_record.player_id,
                    player_name=speech_record.player_name,
                    speech_content=speech_record.speech_content,
                    round_number=speech_record.round_number,
                    phase=speech_record.phase,
                    is_available=is_available
                )
                
                if is_available:
                    available_refs.append(ref_info)
            
            return sorted(available_refs, key=lambda x: (x.round_number, x.player_id))
            
        except Exception as e:
            raise SpeechHistoryError(
                f"Failed to get available references: {str(e)}",
                round_number=current_round
            )
    
    def clear_history(self) -> None:
        """Clear all speech history records."""
        self._speech_records.clear()
        self._player_speech_index.clear()
        self._round_speech_index.clear()
        self._phase_speech_index.clear()
    
    def get_speech_count(self, player_id: Optional[int] = None) -> int:
        """
        Get total speech count.
        
        Args:
            player_id: Optional player ID to get count for specific player
            
        Returns:
            Total number of speeches
        """
        if player_id is None:
            return len(self._speech_records)
        
        return len(self._player_speech_index.get(player_id, []))
    
    def _update_player_index(self, player_id: int, record_index: int) -> None:
        """Update the player speech index."""
        if player_id not in self._player_speech_index:
            self._player_speech_index[player_id] = []
        self._player_speech_index[player_id].append(record_index)
    
    def _update_round_index(self, round_num: int, record_index: int) -> None:
        """Update the round speech index."""
        if round_num not in self._round_speech_index:
            self._round_speech_index[round_num] = []
        self._round_speech_index[round_num].append(record_index)
    
    def _update_phase_index(self, phase: str, record_index: int) -> None:
        """Update the phase speech index."""
        if phase not in self._phase_speech_index:
            self._phase_speech_index[phase] = []
        self._phase_speech_index[phase].append(record_index)
    
    def _cleanup_old_records(self) -> None:
        """Remove old records if we exceed max history length."""
        if len(self._speech_records) <= self.max_history_length:
            return
        
        # Calculate how many records to remove
        records_to_remove = len(self._speech_records) - self.max_history_length
        
        # Remove oldest records
        removed_records = self._speech_records[:records_to_remove]
        self._speech_records = self._speech_records[records_to_remove:]
        
        # Rebuild indices (simple approach - can be optimized)
        self._rebuild_indices()
    
    def _rebuild_indices(self) -> None:
        """Rebuild all indices after cleanup."""
        self._player_speech_index.clear()
        self._round_speech_index.clear()
        self._phase_speech_index.clear()
        
        for index, record in enumerate(self._speech_records):
            self._update_player_index(record.player_id, index)
            self._update_round_index(record.round_number, index)
            self._update_phase_index(record.phase, index)