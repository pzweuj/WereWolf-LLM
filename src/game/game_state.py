from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models.player import Player, Role, PlayerStatus, Team


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
        
        # Day context information
        self.last_words_context: List[Dict[str, Any]] = []
        self.day_speeches: Dict[int, List[Dict[str, Any]]] = {}  # round -> [speech_records]
        self.last_words_printed: Dict[int, bool] = {}  # round -> printed_flag
        
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
            "context_instructions": {
                "reminder": "这是真实的游戏信息，请基于实际发生的事件进行推理",
                "first_round_note": f"这是第一轮游戏，{'但有死亡玩家的遗言信息需要重点关注' if len(last_words_info) > 0 else '没有前夜的查验结果或互动'}" if self.current_round == 1 else None,
                "speech_note": "发言历史包含实际发言内容，如显示'尚未发言'则该玩家确实未发言",
                "last_words_emphasis": f"死亡玩家的遗言包含重要信息，请仔细分析" if len(last_words_info) > 0 else None
            }
        }
    
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