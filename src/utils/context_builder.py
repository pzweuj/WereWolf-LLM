"""
Enhanced Context Builder for providing accurate and complete game context to LLM players.
"""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from ..models.hallucination_models import (
    ContextBuildingError,
    HallucinationReductionConfig
)
from ..models.player import Player
from .speech_history_tracker import SpeechHistoryTracker


class EnhancedContextBuilder:
    """
    Enhanced context builder that provides accurate, complete, and validated
    game context information to prevent hallucinations.
    """
    
    def __init__(self, config: Optional[HallucinationReductionConfig] = None):
        """
        Initialize the enhanced context builder.
        
        Args:
            config: Configuration for context building
        """
        self.config = config or HallucinationReductionConfig()
    
    def build_context(
        self, 
        player_id: int, 
        phase: str, 
        game_state: Any,
        speech_tracker: SpeechHistoryTracker
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for a player.
        
        Args:
            player_id: ID of the player requesting context
            phase: Current game phase
            game_state: Current game state object
            speech_tracker: Speech history tracker
            
        Returns:
            Enhanced context dictionary
        """
        try:
            # Get base context from game state
            base_context = game_state.get_context_for_player(player_id, phase)
            
            # Enhance with speech history
            enhanced_context = self.add_speech_history(base_context, game_state.current_round, speech_tracker)
            
            # Add reality anchors
            enhanced_context = self.add_reality_anchors(enhanced_context, game_state, player_id)
            
            # Validate context completeness
            if self.config.context_validation_enabled:
                is_complete = self.validate_context_completeness(enhanced_context)
                enhanced_context["context_validation"] = {
                    "is_complete": is_complete,
                    "validation_timestamp": datetime.now().isoformat()
                }
            
            return enhanced_context
            
        except Exception as e:
            raise ContextBuildingError(
                f"Failed to build context for player {player_id}: {str(e)}",
                player_id=player_id,
                phase=phase
            )
    
    def add_speech_history(
        self, 
        context: Dict[str, Any], 
        round_num: int,
        speech_tracker: SpeechHistoryTracker
    ) -> Dict[str, Any]:
        """
        Add enhanced speech history to context.
        
        Args:
            context: Base context dictionary
            round_num: Current round number
            speech_tracker: Speech history tracker
            
        Returns:
            Context enhanced with speech history
        """
        try:
            # Get current round speeches
            current_round_speeches = speech_tracker.get_round_speeches(round_num, "day_discussion")
            
            # Get all historical speeches (limited)
            all_speeches = speech_tracker.get_all_speeches(limit=self.config.max_speech_history_length)
            
            # Organize speeches by round
            speeches_by_round = {}
            for speech in all_speeches:
                round_key = speech.round_number
                if round_key not in speeches_by_round:
                    speeches_by_round[round_key] = []
                speeches_by_round[round_key].append({
                    "player_id": speech.player_id,
                    "player_name": speech.player_name,
                    "content": speech.speech_content,
                    "speaking_order": speech.speaking_order,
                    "timestamp": speech.timestamp.isoformat(),
                    "phase": speech.phase
                })
            
            # Add enhanced speech information
            context["enhanced_speech_history"] = {
                "current_round_speeches": [
                    {
                        "player_id": speech.player_id,
                        "player_name": speech.player_name,
                        "content": speech.speech_content,
                        "speaking_order": speech.speaking_order,
                        "timestamp": speech.timestamp.isoformat(),
                        "is_current_round": True
                    }
                    for speech in current_round_speeches
                ],
                "historical_speeches": speeches_by_round,
                "total_speech_count": len(all_speeches),
                "speech_statistics": self._generate_speech_statistics(all_speeches)
            }
            
            # Add speaking order information
            context["speaking_context"] = self._build_speaking_context(
                current_round_speeches, context.get("alive_players", [])
            )
            
            return context
            
        except Exception as e:
            print(f"Error adding speech history to context: {e}")
            return context
    
    def add_reality_anchors(
        self, 
        context: Dict[str, Any], 
        game_state: Any,
        current_player_id: int
    ) -> Dict[str, Any]:
        """
        Add reality anchors to prevent hallucinations.
        
        Args:
            context: Context dictionary to enhance
            game_state: Current game state
            current_player_id: ID of the current player
            
        Returns:
            Context enhanced with reality anchors
        """
        try:
            # Get current player
            current_player = game_state.get_player_by_id(current_player_id)
            
            # Build reality anchors
            reality_anchors = {
                "game_facts": self._build_game_facts(game_state),
                "available_information": self._build_available_information(game_state, current_player),
                "forbidden_information": self._build_forbidden_information(game_state, current_player),
                "player_status": self._build_player_status(game_state),
                "round_constraints": self._build_round_constraints(game_state),
                "role_constraints": self._build_role_constraints(current_player, game_state)
            }
            
            context["reality_anchors"] = reality_anchors
            
            # Add explicit guidance
            context["hallucination_prevention"] = {
                "reminders": [
                    "只能基于真实发生的游戏事件进行推理",
                    "不能编造不存在的玩家互动或发言内容",
                    "身份声明必须符合游戏规则和策略需要",
                    "时间引用必须符合当前游戏进度"
                ],
                "verification_checklist": [
                    "检查引用的发言是否真实存在",
                    "确认身份声明的准确性",
                    "验证时间引用的合理性",
                    "避免编造玩家间的具体互动"
                ]
            }
            
            return context
            
        except Exception as e:
            print(f"Error adding reality anchors to context: {e}")
            return context
    
    def validate_context_completeness(self, context: Dict[str, Any]) -> bool:
        """
        Validate that the context contains all necessary information.
        
        Args:
            context: Context dictionary to validate
            
        Returns:
            True if context is complete, False otherwise
        """
        try:
            required_sections = [
                "round",
                "phase", 
                "alive_players",
                "all_players"
            ]
            
            # Check required sections
            for section in required_sections:
                if section not in context:
                    print(f"Context validation failed: missing section '{section}'")
                    return False
            
            # Check enhanced sections if enabled
            if self.config.enable_reality_anchors:
                if "reality_anchors" not in context:
                    print("Context validation failed: missing reality anchors")
                    return False
            
            # Check speech history if available
            if "enhanced_speech_history" in context:
                speech_history = context["enhanced_speech_history"]
                if "current_round_speeches" not in speech_history:
                    print("Context validation failed: missing current round speeches")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error validating context completeness: {e}")
            return False
    
    def _generate_speech_statistics(self, speeches: List[Any]) -> Dict[str, Any]:
        """Generate statistics about speech history."""
        
        if not speeches:
            return {"total_speeches": 0, "speeches_by_player": {}, "speeches_by_round": {}}
        
        stats = {
            "total_speeches": len(speeches),
            "speeches_by_player": {},
            "speeches_by_round": {}
        }
        
        for speech in speeches:
            # Count by player
            player_id = speech.player_id
            if player_id not in stats["speeches_by_player"]:
                stats["speeches_by_player"][player_id] = {
                    "name": speech.player_name,
                    "count": 0
                }
            stats["speeches_by_player"][player_id]["count"] += 1
            
            # Count by round
            round_num = speech.round_number
            if round_num not in stats["speeches_by_round"]:
                stats["speeches_by_round"][round_num] = 0
            stats["speeches_by_round"][round_num] += 1
        
        return stats
    
    def _build_speaking_context(
        self, 
        current_speeches: List[Any], 
        alive_players: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build context about speaking order and status."""
        
        # Get players who have spoken
        spoken_player_ids = {speech.player_id for speech in current_speeches}
        
        # Categorize players
        players_who_spoke = []
        players_yet_to_speak = []
        
        for player in alive_players:
            player_id = player.get("id")
            if player_id in spoken_player_ids:
                players_who_spoke.append(player)
            else:
                players_yet_to_speak.append(player)
        
        return {
            "players_who_spoke": players_who_spoke,
            "players_yet_to_speak": players_yet_to_speak,
            "speaking_progress": {
                "total_alive": len(alive_players),
                "spoken": len(players_who_spoke),
                "remaining": len(players_yet_to_speak)
            }
        }
    
    def _build_game_facts(self, game_state: Any) -> Dict[str, Any]:
        """Build fundamental game facts."""
        
        return {
            "current_round": game_state.current_round,
            "current_phase": game_state.phase,
            "total_players": len(game_state.players),
            "alive_players": len(game_state.get_alive_players()),
            "dead_players": len(game_state.get_dead_players()),
            "game_started": game_state.current_round > 0,
            "is_first_round": game_state.current_round == 1
        }
    
    def _build_available_information(self, game_state: Any, player: Optional[Player]) -> List[str]:
        """Build list of information available to the player."""
        
        available_info = [
            "玩家列表和编号",
            "存活和死亡玩家状态",
            "当前轮次和阶段信息"
        ]
        
        if game_state.current_round > 1:
            available_info.extend([
                "历史发言记录",
                "历史投票结果",
                "已淘汰玩家信息"
            ])
        
        # Add night death information
        if hasattr(game_state, 'deaths_this_night') and game_state.deaths_this_night:
            available_info.append("夜晚死亡公告")
        
        # Add last words if available
        if hasattr(game_state, 'last_words_context') and game_state.last_words_context:
            available_info.append("死亡玩家遗言")
        
        return available_info
    
    def _build_forbidden_information(self, game_state: Any, player: Optional[Player]) -> List[str]:
        """Build list of information that should not be referenced."""
        
        forbidden_info = [
            "其他玩家的真实身份（除非公开声明）",
            "私人夜间行动结果（除非是自己的）",
            "编造的玩家互动或对话"
        ]
        
        if game_state.current_round == 1:
            forbidden_info.extend([
                "前夜查验结果",
                "复杂的历史行为分析",
                "不存在的投票历史",
                "虚构的玩家关系"
            ])
        
        return forbidden_info
    
    def _build_player_status(self, game_state: Any) -> Dict[str, Any]:
        """Build comprehensive player status information."""
        
        player_status = {
            "alive_players": [],
            "dead_players": [],
            "player_details": {}
        }
        
        for player in game_state.players:
            player_info = {
                "id": player.id,
                "name": player.name,
                "status": "alive" if player.is_alive() else "dead"
            }
            
            if player.is_alive():
                player_status["alive_players"].append(player_info)
            else:
                player_status["dead_players"].append(player_info)
            
            player_status["player_details"][player.id] = player_info
        
        return player_status
    
    def _build_round_constraints(self, game_state: Any) -> Dict[str, Any]:
        """Build constraints based on current round."""
        
        constraints = {
            "current_round": game_state.current_round,
            "is_first_round": game_state.current_round == 1,
            "max_rounds": getattr(game_state, 'max_rounds', 10)
        }
        
        if game_state.current_round == 1:
            constraints["first_round_limitations"] = [
                "没有前夜信息可供分析",
                "没有历史投票记录",
                "没有复杂的玩家互动历史",
                "应该基于基础游戏规则进行推理"
            ]
        
        return constraints
    
    def _build_role_constraints(self, player: Optional[Player], game_state: Any) -> Dict[str, Any]:
        """Build role-specific constraints."""
        
        if not player:
            return {}
        
        constraints = {
            "player_role": player.role.value,
            "can_claim_roles": [],
            "should_avoid_claiming": []
        }
        
        # Define what roles this player can reasonably claim
        from ..models.player import Role
        
        if player.role == Role.VILLAGER:
            constraints["can_claim_roles"] = ["村民"]
            constraints["should_avoid_claiming"] = ["预言家", "女巫", "猎人", "狼人"]
        elif player.role == Role.SEER:
            constraints["can_claim_roles"] = ["预言家", "村民"]  # Can claim villager as strategy
            constraints["should_avoid_claiming"] = ["女巫", "猎人", "狼人"]
        elif player.role == Role.WITCH:
            constraints["can_claim_roles"] = ["女巫", "村民"]
            constraints["should_avoid_claiming"] = ["预言家", "猎人", "狼人"]
        elif player.role == Role.HUNTER:
            constraints["can_claim_roles"] = ["猎人", "村民"]
            constraints["should_avoid_claiming"] = ["预言家", "女巫", "狼人"]
        elif player.role == Role.WEREWOLF:
            constraints["can_claim_roles"] = ["村民", "预言家", "女巫", "猎人"]  # Can fake any role
            constraints["should_avoid_claiming"] = ["狼人"]
        
        return constraints