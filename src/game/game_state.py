from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models.player import Player, Role, PlayerStatus, Team
from ..utils.speech_history_tracker import SpeechHistoryTracker


class VoteRecord:
    def __init__(self, round_num: int, voter_id: int, target_id: int):
        self.round_num = round_num
        self.voter_id = voter_id
        self.target_id = target_id
        self.timestamp = datetime.now()


class GameState:
    def __init__(self):
        self.players: List[Player] = []
        self.current_round = 0
        self.phase = "setup"  # setup, night, day, voting, ended
        self.game_start_time = datetime.now()
        self.vote_records: List[VoteRecord] = []
        
        # Night events tracking
        self.night_actions: Dict[int, Dict[str, Any]] = {}  # player_id -> action
        self.wolf_kill_target: Optional[int] = None
        self.seer_check_result: Optional[str] = None
        self.witch_heal_used = False
        self.witch_poison_used = False
        self.hunter_shot: Optional[int] = None
        
        # Death tracking
        self.deaths_this_night: List[int] = []
        self.deaths_this_day: List[int] = []
        
        # Game settings
        self.first_night_has_witness = True  # 首夜死亡有遗言
        self.max_rounds = 10  # 防止无限游戏
        
        # Enhanced speech tracking system
        self.speech_history_tracker = SpeechHistoryTracker()
        
        # Day context information (legacy - will be gradually replaced by speech_history_tracker)
        self.last_words_context: List[Dict[str, Any]] = []
        self.day_speeches: Dict[int, List[Dict[str, Any]]] = {}  # round -> [speech_records]
        self.last_words_printed: Dict[int, bool] = {}  # round -> printed_flag
        self.all_last_words: List[Dict[str, Any]] = []  # 所有轮次的遗言历史
        self.voting_history: List[Dict[str, Any]] = []  # 投票历史记录
        
    def add_player(self, player: Player):
        """Add a player to the game"""
        self.players.append(player)
    
    def get_alive_players(self) -> List[Player]:
        """Get all alive players"""
        return [p for p in self.players if p.is_alive()]
    
    def get_dead_players(self) -> List[Player]:
        """Get all dead players"""
        return [p for p in self.players if not p.is_alive()]
    
    def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """Get player by ID"""
        for player in self.players:
            if player.id == player_id:
                return player
        return None
    
    def get_players_by_role(self, role: Role) -> List[Player]:
        """Get all players with a specific role"""
        return [p for p in self.players if p.role == role]
    
    def get_alive_players_by_role(self, role: Role) -> List[Player]:
        """Get all alive players with a specific role"""
        return [p for p in self.players if p.role == role and p.is_alive()]
    
    def get_wolf_players(self) -> List[Player]:
        """Get all wolf players"""
        return self.get_players_by_role(Role.WEREWOLF)
    
    def get_alive_wolf_players(self) -> List[Player]:
        """Get all alive wolf players"""
        return self.get_alive_players_by_role(Role.WEREWOLF)
    
    def get_villager_players(self) -> List[Player]:
        """Get all non-wolf players"""
        return [p for p in self.players if p.team == Team.VILLAGER]
    
    def get_alive_villager_players(self) -> List[Player]:
        """Get all alive non-wolf players"""
        return [p for p in self.players if p.team == Team.VILLAGER and p.is_alive()]
    
    def kill_player(self, player_id: int) -> bool:
        """Kill a player and return if successful"""
        player = self.get_player_by_id(player_id)
        if player and player.is_alive():
            player.kill()
            return True
        return False
    
    def record_vote(self, voter_id: int, target_id: int):
        """Record a vote"""
        vote = VoteRecord(self.current_round, voter_id, target_id)
        self.vote_records.append(vote)
    
    def get_votes_this_round(self) -> List[VoteRecord]:
        """Get all votes for current round"""
        return [v for v in self.vote_records if v.round_num == self.current_round]
    
    def get_vote_count(self) -> Dict[int, int]:
        """Get vote count for current round"""
        votes = self.get_votes_this_round()
        vote_count = {}
        for vote in votes:
            vote_count[vote.target_id] = vote_count.get(vote.target_id, 0) + 1
        return vote_count
    
    def get_most_voted_player(self) -> Optional[int]:
        """Get the player with most votes (for elimination)"""
        vote_count = self.get_vote_count()
        if not vote_count:
            return None
        
        max_votes = max(vote_count.values())
        most_voted = [pid for pid, votes in vote_count.items() if votes == max_votes]
        
        # Return the first if there's a tie
        return most_voted[0] if len(most_voted) == 1 else None
    
    def check_victory_conditions(self) -> Dict[str, Any]:
        """Check if game has ended and return result"""
        alive_wolves = len(self.get_alive_wolf_players())
        alive_villagers = len(self.get_alive_villager_players())
        alive_players = len(self.get_alive_players())
        
        # Wolf victory conditions
        if alive_wolves == 0:
            return {"game_over": True, "winner": "villagers", "reason": "所有狼人被淘汰"}
        
        if alive_wolves >= alive_villagers:
            return {"game_over": True, "winner": "werewolves", "reason": "狼人人数大于等于好人"}
        
        # Check if witch has no potions left and it's 1v1
        witch = self.get_players_by_role(Role.WITCH)
        if witch and not witch[0].is_alive():
            witch_potions_used = not witch[0].witch_potions["heal"] and not witch[0].witch_potions["poison"]
            if witch_potions_used and alive_wolves == 1 and alive_villagers == 1:
                return {"game_over": True, "winner": "werewolves", "reason": "女巫药物已用完，1v1狼人胜利"}
        
        # Check max rounds
        if self.current_round >= self.max_rounds:
            return {"game_over": True, "winner": "draw", "reason": "达到最大回合数"}
        
        return {"game_over": False, "winner": None, "reason": None}
    
    def get_game_summary(self) -> Dict[str, Any]:
        """Get current game summary"""
        alive_players = self.get_alive_players()
        dead_players = self.get_dead_players()
        
        return {
            "round": self.current_round,
            "phase": self.phase,
            "alive_players": [{"id": p.id, "name": p.name, "role": p.role.value} for p in alive_players],
            "dead_players": [{"id": p.id, "name": p.name, "role": p.role.value} for p in dead_players],
            "alive_wolves": len(self.get_alive_wolf_players()),
            "alive_villagers": len(self.get_alive_villager_players()),
            "game_duration": str(datetime.now() - self.game_start_time)
        }
    
    def next_round(self):
        """Move to next round"""
        # 保存当前轮次的遗言到历史记录
        if self.last_words_context:
            for last_word in self.last_words_context:
                if last_word not in self.all_last_words:
                    self.all_last_words.append(last_word)
        
        self.current_round += 1
        self.phase = "night"
        self.night_actions.clear()
        self.wolf_kill_target = None
        self.seer_check_result = None
        self.witch_heal_used = False
        self.witch_poison_used = False
        self.hunter_shot = None
        self.deaths_this_night.clear()
        self.deaths_this_day.clear()
        
        # 清空当前轮次的遗言上下文，但保留历史记录
        self.last_words_context.clear()
    
    def get_context_for_player(self, player_id: int, context_type: str = "public") -> Dict[str, Any]:
        """Get specific context based on player role and context type"""
        player = self.get_player_by_id(player_id)
        if not player:
            return {}
        
        alive_players = self.get_alive_players()
        dead_players = self.get_dead_players()
        
        # Get player names mapping
        player_names = {p.id: p.name for p in self.players}
        
        if context_type == "seer" and player.role == Role.SEER:
            return self._get_seer_context(player)
        elif context_type == "wolf" and player.role == Role.WEREWOLF:
            return self._get_wolf_context(player)
        elif context_type == "witch" and player.role == Role.WITCH:
            return self._get_witch_context(player)
        elif context_type == "day":
            return self._get_day_context(player)
        else:
            return self._get_basic_context(player)
    
    def _get_seer_context(self, player: Player) -> Dict[str, Any]:
        """Private context for seer"""
        alive_players = self.get_alive_players()
        dead_players = self.get_dead_players()
        
        # Build unchecked players list with names and status
        unchecked_players = [p for p in alive_players 
                           if p.id != player.id and p.id not in player.seer_checks]
        
        unchecked_info = []
        for target_player in unchecked_players:
            unchecked_info.append({
                "id": target_player.id,
                "name": target_player.name,
                "role_display": "未知",
                "status": "alive"
            })
        
        # Include all players with their current status
        all_players_info = []
        for p in self.players:
            all_players_info.append({
                "id": p.id,
                "name": p.name,
                "status": "alive" if p.is_alive() else "dead",
                "role": p.role.value
            })

        return {
            "context_type": "seer_private",
            "round": self.current_round,
            "phase": self.phase,
            "unchecked_players": unchecked_info,
            "seer_checks": player.seer_checks,
            "all_players": all_players_info,
            "alive_players": [{"id": p.id, "name": p.name} for p in alive_players],
            "dead_players": [{"id": p.id, "name": p.name} for p in dead_players],
            "instruction": "你必须选择一名玩家进行查验，使用CHECK: [ID]格式"
        }
    
    def _get_wolf_context(self, player: Player) -> Dict[str, Any]:
        """Wolf team shared context -狼人看不到好人身份"""
        alive_players = self.get_alive_players()
        dead_players = self.get_dead_players()
        wolf_team = [p for p in alive_players if p.role == Role.WEREWOLF]
        non_wolf_players = [p for p in alive_players if p.role != Role.WEREWOLF]
        
        wolf_info = [{"id": p.id, "name": p.name, "status": "alive"} for p in wolf_team]
        
        # 狼人视角：好人都是"村民"，看不到真实身份
        target_info = [{"id": p.id, "name": p.name, "role_display": "村民", "status": "alive"} for p in non_wolf_players]
        target_ids = [p.id for p in non_wolf_players]
        
        # Include all players with their current status
        all_players_info = []
        for p in self.players:
            all_players_info.append({
                "id": p.id,
                "name": p.name,
                "status": "alive" if p.is_alive() else "dead",
                "role_display": "狼人" if p.role == Role.WEREWOLF else "村民"
            })

        return {
            "context_type": "wolf_team_private",
            "round": self.current_round,
            "phase": self.phase,
            "wolf_team": wolf_info,
            "available_targets": target_ids,
            "all_players": all_players_info,
            "alive_players": [{"id": p.id, "name": p.name} for p in alive_players],
            "dead_players": [{"id": p.id, "name": p.name} for p in dead_players],
            "target_info": target_info,  # Keep for display purposes
            "instruction": "狼人团队必须统一选择击杀目标，使用KILL: [ID]格式"
        }
    
    def _get_witch_context(self, player: Player) -> Dict[str, Any]:
        """Private context for witch"""
        alive_players = self.get_alive_players()
        dead_players = self.get_dead_players()
        
        # Get killed player info
        killed_player = None
        if hasattr(self, 'wolf_kill_target') and self.wolf_kill_target:
            kp = self.get_player_by_id(self.wolf_kill_target)
            if kp and kp.is_alive():
                killed_player = {"id": kp.id, "name": kp.name, "status": "alive"}
        
        # Build poisoning targets
        poison_targets = [{"id": p.id, "name": p.name, "status": "alive"} 
                         for p in alive_players if p.id != player.id]
        
        # Include all players with their current status
        all_players_info = []
        for p in self.players:
            all_players_info.append({
                "id": p.id,
                "name": p.name,
                "status": "alive" if p.is_alive() else "dead",
                "role": p.role.value
            })

        return {
            "context_type": "witch_private",
            "round": self.current_round,
            "phase": self.phase,
            "killed_player": killed_player,
            "heal_potion": player.witch_potions["heal"],
            "poison_potion": player.witch_potions["poison"],
            "poison_targets": poison_targets,
            "all_players": all_players_info,
            "alive_players": [{"id": p.id, "name": p.name} for p in alive_players],
            "dead_players": [{"id": p.id, "name": p.name} for p in dead_players],
            "instruction": "你必须做出选择：heal/poison/none"
        }
    
    def _get_day_context(self, player: Player) -> Dict[str, Any]:
        """Public day discussion context"""
        alive_players = self.get_alive_players()
        dead_players = self.get_dead_players()
        
        # Speaking order calculation
        alive_sorted = sorted(alive_players, key=lambda p: p.id)
        speaking_order = [p.id for p in alive_sorted]
        player_index = speaking_order.index(player.id) if player.id in speaking_order else -1
        
        players_who_spoke = [p for p in alive_sorted if p.id < player.id]
        players_remaining = [p for p in alive_sorted if p.id > player.id]
        
        # Build public speech history with actual content (without revealing roles)
        speech_history = []
        for p in players_who_spoke:
            # Get actual speech from current round's day speeches
            actual_speech = self._get_player_speech_in_round(p.id, self.current_round)
            speech_history.append({
                "id": p.id,
                "name": p.name,
                "status": "alive" if p.is_alive() else "dead",
                "speech": actual_speech if actual_speech else f"[玩家{p.name}尚未发言]"
            })
        
        # Enhanced last words processing with validation and formatting
        last_words_info = []
        if hasattr(self, 'last_words_context') and self.last_words_context:
            # Only print debug info and last words once per round
            if not self.last_words_printed.get(self.current_round, False):
                print(f"🔍 DEBUG: 处理遗言信息 - 共 {len(self.last_words_context)} 条遗言")
                self.last_words_printed[self.current_round] = True
                
                # Print each last word only once per round
                for last_word in self.last_words_context:
                    if self._validate_last_word_entry(last_word):
                        print(f"😒遗言 - {last_word['name']}({last_word['player']}): {last_word['speech']}")
            
            # Always process last words for context (but don't print again)
            for last_word in self.last_words_context:
                if self._validate_last_word_entry(last_word):
                    formatted_last_word = {
                        "player": last_word["player"],
                        "name": last_word["name"],
                        "speech": last_word["speech"],
                        "round": getattr(last_word, 'round', self.current_round),
                        "death_reason": last_word.get("death_reason", "夜晚死亡"),
                        "is_last_words": True
                    }
                    last_words_info.append(formatted_last_word)
        else:
            # Only print this debug message once per round
            if not self.last_words_printed.get(self.current_round, False):
                print(f"🔍 DEBUG: 无遗言信息可用")
                self.last_words_printed[self.current_round] = True
        
        # Include all players with their current status
        all_players_info = []
        for p in self.players:
            all_players_info.append({
                "id": p.id,
                "name": p.name,
                "status": "alive" if p.is_alive() else "dead",
                "role_display": "未知"  # 白天阶段不暴露角色
            })

        # Add clear round and phase information to prevent hallucinations
        game_stage_info = {
            "is_first_round": self.current_round == 1,
            "round_number": self.current_round,
            "phase_name": "白天讨论阶段",
            "has_previous_night": self.current_round > 1,
            "game_just_started": self.current_round == 1
        }
        
        # Add explicit context about what information is available
        available_info = {
            "night_deaths_announced": True,
            "last_words_available": len(last_words_info) > 0,
            "previous_day_speeches": self.current_round > 1,
            "seer_results_available": False,  # Players don't know seer results in public
            "previous_voting_results": self.current_round > 1
        }
        
        # Add reality constraints information
        reality_constraints = {
            "current_round": self.current_round,
            "is_first_round": self.current_round == 1,
            "available_information": self._get_available_information(),
            "forbidden_claims": self._get_forbidden_claims(player),
            "required_disclaimers": self._get_required_disclaimers()
        }
        
        # 添加历史信息
        historical_context = self._build_historical_context()
        
        return {
            "context_type": "day_public",
            "round": self.current_round,
            "phase": self.phase,
            "game_stage": game_stage_info,
            "available_information": available_info,
            "alive_players": [{"id": p.id, "name": p.name, "status": "alive"} for p in alive_players],
            "dead_players": [{"id": p.id, "name": p.name, "status": "dead"} for p in dead_players],
            "all_players": all_players_info,
            "speaking_order": speaking_order,
            "my_position": player_index + 1,
            "speech_history": speech_history,
            "last_words": last_words_info,
            "players_before_me": [
                {"id": p.id, "name": p.name, "status": "alive" if p.is_alive() else "dead"} 
                for p in players_who_spoke
            ],
            "players_after_me": [
                {"id": p.id, "name": p.name, "status": "alive" if p.is_alive() else "dead"}
                for p in players_remaining
            ],
            "historical_context": historical_context,  # 添加历史上下文
            "reality_constraints": reality_constraints,  # 添加现实约束信息
            "context_instructions": {
                "reminder": "这是真实的游戏信息，请基于实际发生的事件进行推理",
                "first_round_note": f"这是第一轮游戏，{'但有死亡玩家的遗言信息需要重点关注' if len(last_words_info) > 0 else '没有前夜的查验结果或互动'}" if self.current_round == 1 else None,
                "speech_note": "发言历史包含实际发言内容，如显示'尚未发言'则该玩家确实未发言",
                "last_words_emphasis": f"死亡玩家的遗言包含重要信息，请仔细分析" if len(last_words_info) > 0 else None,
                "historical_note": "历史信息包含之前轮次的重要内容，请结合历史信息进行分析" if historical_context["has_history"] else None
            }
        }
        
        # Apply first round filtering if needed
        if self.current_round == 1:
            return self._filter_context_for_first_round(context)
        
        return context
    
    def _validate_last_word_entry(self, last_word: Dict[str, Any]) -> bool:
        """Validate last word entry format and content"""
        required_fields = ["player", "name", "speech"]
        
        # Check if all required fields are present
        for field in required_fields:
            if field not in last_word:
                print(f"🔍 DEBUG: 遗言验证失败 - 缺少字段: {field}")
                return False
        
        # Check if player ID is valid
        if not isinstance(last_word["player"], int) or last_word["player"] <= 0:
            print(f"🔍 DEBUG: 遗言验证失败 - 无效玩家ID: {last_word['player']}")
            return False
        
        # Check if name is not empty
        if not last_word["name"] or not isinstance(last_word["name"], str):
            print(f"🔍 DEBUG: 遗言验证失败 - 无效玩家姓名: {last_word['name']}")
            return False
        
        # Check if speech is not empty
        if not last_word["speech"] or not isinstance(last_word["speech"], str):
            print(f"🔍 DEBUG: 遗言验证失败 - 无效遗言内容: {last_word['speech']}")
            return False
        
        return True
    
    def add_last_words(self, player_id: int, speech: str, death_reason: str = "夜晚死亡") -> bool:
        """Add last words to the context for day discussion"""
        player = self.get_player_by_id(player_id)
        if not player:
            print(f"🔍 DEBUG: 添加遗言失败 - 找不到玩家: {player_id}")
            return False
        
        last_word_entry = {
            "player": player_id,
            "name": player.name,
            "speech": speech,
            "round": self.current_round,
            "death_reason": death_reason,
            "is_last_words": True
        }
        
        if self._validate_last_word_entry(last_word_entry):
            self.last_words_context.append(last_word_entry)
            print(f"🔍 DEBUG: 成功添加遗言 - {player.name}({player_id}): {speech[:50]}...")
            return True
        else:
            print(f"🔍 DEBUG: 添加遗言失败 - 验证不通过")
            return False
    
    def _get_player_speech_in_round(self, player_id: int, round_num: int) -> Optional[str]:
        """Get player's speech in a specific round"""
        if round_num not in self.day_speeches:
            return None
        
        for speech_record in self.day_speeches[round_num]:
            if speech_record.get("player") == player_id:
                return speech_record.get("speech")
        
        return None
    
    def record_day_speech(self, player_id: int, speech: str, speaking_order: int = 0) -> bool:
        """Record a player's speech during day discussion"""
        player = self.get_player_by_id(player_id)
        if not player:
            return False
        
        # Record in enhanced speech history tracker
        try:
            success = self.speech_history_tracker.record_speech(
                player_id=player_id,
                player_name=player.name,
                speech=speech,
                round_num=self.current_round,
                phase="day_discussion",
                speaking_order=speaking_order
            )
            
            if not success:
                print(f"Warning: Failed to record speech in enhanced tracker for player {player_id}")
        except Exception as e:
            print(f"Error recording speech in enhanced tracker: {e}")
        
        # Also maintain legacy format for backward compatibility
        if self.current_round not in self.day_speeches:
            self.day_speeches[self.current_round] = []
        
        speech_record = {
            "player": player_id,
            "name": player.name,
            "speech": speech,
            "speaking_order": speaking_order,
            "round": self.current_round,
            "phase": "day_discussion"
        }
        
        self.day_speeches[self.current_round].append(speech_record)
        return True
    
    def get_enhanced_speech_history(self, current_player_id: int) -> Dict[str, Any]:
        """Get enhanced speech history using the SpeechHistoryTracker"""
        try:
            # Get all speeches for current round
            current_round_speeches = self.speech_history_tracker.get_round_speeches(self.current_round, "day_discussion")
            
            # Get available references for the current player
            available_refs = self.speech_history_tracker.get_available_references(
                self.current_round, 
                "day_discussion", 
                exclude_player_id=current_player_id
            )
            
            # Get all speeches from previous rounds
            all_speeches = self.speech_history_tracker.get_all_speeches(limit=50)
            
            return {
                "current_round_speeches": [
                    {
                        "player_id": speech.player_id,
                        "player_name": speech.player_name,
                        "content": speech.speech_content,
                        "speaking_order": speech.speaking_order,
                        "timestamp": speech.timestamp.isoformat()
                    }
                    for speech in current_round_speeches
                ],
                "available_references": [
                    {
                        "player_id": ref.player_id,
                        "player_name": ref.player_name,
                        "content": ref.speech_content[:100] + "..." if len(ref.speech_content) > 100 else ref.speech_content,
                        "round": ref.round_number,
                        "phase": ref.phase
                    }
                    for ref in available_refs
                ],
                "total_speeches": len(all_speeches),
                "speech_count_by_player": {
                    player.id: self.speech_history_tracker.get_speech_count(player.id)
                    for player in self.players
                }
            }
        except Exception as e:
            print(f"Error getting enhanced speech history: {e}")
            return {
                "current_round_speeches": [],
                "available_references": [],
                "total_speeches": 0,
                "speech_count_by_player": {}
            }
    
    def verify_player_speech_reference(self, claimed_speech: str, claimed_speaker_id: int) -> Dict[str, Any]:
        """Verify if a speech reference is valid using enhanced tracker"""
        try:
            is_valid = self.speech_history_tracker.verify_speech_reference(claimed_speech, claimed_speaker_id)
            best_match, similarity = self.speech_history_tracker.find_best_speech_match(claimed_speech, claimed_speaker_id)
            
            return {
                "is_valid": is_valid,
                "best_match": {
                    "content": best_match.speech_content if best_match else None,
                    "similarity": similarity,
                    "round": best_match.round_number if best_match else None,
                    "phase": best_match.phase if best_match else None
                } if best_match else None,
                "verification_details": {
                    "claimed_speech": claimed_speech,
                    "claimed_speaker_id": claimed_speaker_id,
                    "speaker_name": self.get_player_by_id(claimed_speaker_id).name if self.get_player_by_id(claimed_speaker_id) else "Unknown"
                }
            }
        except Exception as e:
            print(f"Error verifying speech reference: {e}")
            return {
                "is_valid": False,
                "best_match": None,
                "verification_details": {
                    "error": str(e)
                }
            }
    
    def verify_identity_claim_reference(self, claimed_identity: str, claimed_speaker_id: int) -> Dict[str, Any]:
        """Verify if an identity claim reference is valid"""
        try:
            is_valid = self.speech_history_tracker.verify_identity_claim_reference(claimed_identity, claimed_speaker_id)
            all_claims = self.speech_history_tracker.get_player_identity_claims(claimed_speaker_id)
            
            return {
                "is_valid": is_valid,
                "claimed_identity": claimed_identity,
                "speaker_id": claimed_speaker_id,
                "speaker_name": self.get_player_by_id(claimed_speaker_id).name if self.get_player_by_id(claimed_speaker_id) else "Unknown",
                "all_identity_claims": all_claims,
                "has_made_identity_claims": len(all_claims) > 0
            }
        except Exception as e:
            print(f"Error verifying identity claim reference: {e}")
            return {
                "is_valid": False,
                "claimed_identity": claimed_identity,
                "error": str(e)
            }
    
    def get_speech_statistics(self) -> Dict[str, Any]:
        """Get comprehensive speech statistics"""
        try:
            stats = {
                "total_speeches": self.speech_history_tracker.get_speech_count(),
                "speeches_by_player": {},
                "speeches_by_round": {},
                "identity_claims_summary": {}
            }
            
            # Get statistics for each player
            for player in self.players:
                player_speech_count = self.speech_history_tracker.get_speech_count(player.id)
                player_identity_claims = self.speech_history_tracker.get_player_identity_claims(player.id)
                
                stats["speeches_by_player"][player.id] = {
                    "name": player.name,
                    "speech_count": player_speech_count,
                    "identity_claims": player_identity_claims
                }
                
                if player_identity_claims:
                    stats["identity_claims_summary"][player.id] = {
                        "name": player.name,
                        "claims": player_identity_claims
                    }
            
            # Get statistics by round
            for round_num in range(1, self.current_round + 1):
                round_speeches = self.speech_history_tracker.get_round_speeches(round_num)
                stats["speeches_by_round"][round_num] = len(round_speeches)
            
            return stats
        except Exception as e:
            print(f"Error getting speech statistics: {e}")
            return {
                "total_speeches": 0,
                "speeches_by_player": {},
                "speeches_by_round": {},
                "identity_claims_summary": {},
                "error": str(e)
            }
    
    def _build_historical_context(self) -> Dict[str, Any]:
        """构建历史上下文信息"""
        historical_context = {
            "has_history": False,
            "previous_rounds": [],
            "all_last_words": [],
            "voting_history": [],
            "eliminated_players": []
        }
        
        # 如果是第一轮，没有历史信息
        if self.current_round <= 1:
            return historical_context
        
        historical_context["has_history"] = True
        
        # 添加所有历史遗言
        if self.all_last_words:
            historical_context["all_last_words"] = [
                {
                    "round": lw.get("round", 1),
                    "player_id": lw["player"],
                    "player_name": lw["name"],
                    "last_words": lw["speech"],
                    "death_reason": lw.get("death_reason", "夜晚死亡")
                }
                for lw in self.all_last_words
            ]
        
        # 添加历史发言记录
        previous_rounds_data = []
        for round_num in range(1, self.current_round):
            if round_num in self.day_speeches:
                round_speeches = self.day_speeches[round_num]
                previous_rounds_data.append({
                    "round": round_num,
                    "speeches": [
                        {
                            "player_id": speech["player"],
                            "player_name": speech["name"],
                            "speech": speech["speech"][:100] + "..." if len(speech["speech"]) > 100 else speech["speech"],  # 截断长发言
                            "speaking_order": speech.get("speaking_order", 0)
                        }
                        for speech in round_speeches
                    ]
                })
        
        historical_context["previous_rounds"] = previous_rounds_data
        
        # 添加投票历史
        if self.voting_history:
            historical_context["voting_history"] = self.voting_history
        
        # 添加已淘汰玩家信息
        dead_players = self.get_dead_players()
        if dead_players:
            historical_context["eliminated_players"] = [
                {
                    "player_id": p.id,
                    "player_name": p.name,
                    "role": p.role.value,
                    "elimination_round": getattr(p, 'elimination_round', 'unknown')
                }
                for p in dead_players
            ]
        
        return historical_context
    
    def record_voting_result(self, round_num: int, eliminated_player: Optional[int], vote_count: Dict[int, int]):
        """记录投票结果到历史"""
        voting_record = {
            "round": round_num,
            "eliminated_player": eliminated_player,
            "vote_count": vote_count,
            "timestamp": datetime.now()
        }
        
        if eliminated_player:
            eliminated_player_obj = self.get_player_by_id(eliminated_player)
            if eliminated_player_obj:
                voting_record["eliminated_name"] = eliminated_player_obj.name
                voting_record["eliminated_role"] = eliminated_player_obj.role.value
        
        self.voting_history.append(voting_record)
    
    def _get_available_information(self) -> List[str]:
        """获取当前轮次可用的信息类型"""
        available = ["玩家列表和编号", "夜晚死亡公告"]
        
        if hasattr(self, 'last_words_context') and self.last_words_context:
            available.append("死亡玩家遗言")
        
        if self.current_round > 1:
            available.extend([
                "历史发言记录",
                "历史投票结果",
                "已淘汰玩家信息"
            ])
        
        return available
    
    def _get_forbidden_claims(self, player: Player) -> List[str]:
        """获取该玩家禁止声称的身份"""
        forbidden = []
        
        if player.role == Role.VILLAGER:
            forbidden = ["预言家", "女巫", "猎人", "狼人"]
        elif player.role == Role.WEREWOLF:
            # 狼人可以假跳，但需要策略理由
            forbidden = []  # 允许策略性假跳
        elif player.role == Role.SEER:
            forbidden = ["女巫", "猎人", "狼人"]
        elif player.role == Role.WITCH:
            forbidden = ["预言家", "猎人", "狼人"]
        elif player.role == Role.HUNTER:
            forbidden = ["预言家", "女巫", "狼人"]
        
        return forbidden
    
    def _get_required_disclaimers(self) -> List[str]:
        """获取必要的免责声明和约束提醒"""
        disclaimers = [
            "只能基于真实发生的游戏事件进行推理",
            "不能编造不存在的玩家互动或发言内容",
            "身份声明必须符合游戏规则和策略需要"
        ]
        
        if self.current_round == 1:
            disclaimers.extend([
                "第一轮游戏没有前夜信息可供分析",
                "不能引用不存在的历史互动或查验结果",
                "应该基于基础游戏规则进行推理"
            ])
        
        return disclaimers
    
    def _filter_context_for_first_round(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """为第一轮游戏过滤上下文信息"""
        if self.current_round != 1:
            return context
        
        # 为第一轮添加特殊约束
        first_round_constraints = {
            "no_previous_night_info": True,
            "no_interaction_history": True,
            "focus_on_basic_logic": True,
            "available_info_only": [
                "夜晚死亡公告",
                "死亡玩家遗言（如果有）",
                "玩家列表和编号"
            ],
            "forbidden_references": [
                "前夜查验结果",
                "复杂互动分析",
                "历史行为模式",
                "投票历史"
            ]
        }
        
        context["first_round_constraints"] = first_round_constraints
        context["guidance"] = {
            "analysis_focus": "遗言信息和基础游戏规则",
            "avoid_topics": ["前夜查验", "复杂互动", "历史行为"],
            "recommended_approach": "谨慎分析，基于事实发言"
        }
        
        return context
    
    def _get_basic_context(self, player: Player) -> Dict[str, Any]:
        """Basic context for general use"""
        return {
            "player_info": {
                "id": player.id,
                "name": player.name,
                "role": player.role.value,
                "is_alive": player.is_alive()
            }
        }