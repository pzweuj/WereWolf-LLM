from typing import List, Dict, Any, Optional
from ..models.player import Role, PlayerStatus
from ..game.game_state import GameState


class DayPhase:
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.day_events = []
        
    def execute_day_phase(self, night_deaths: List[int]) -> Dict[str, Any]:
        """Execute the complete day phase"""
        print(f"=== 第{self.game_state.current_round}轮白天开始 ===")
        
        self.day_events.clear()
        self.game_state.deaths_this_day.clear()
        
        # 1. Announce night deaths
        death_announcement = self._announce_deaths(night_deaths)
        
        # 2. Handle last words (if applicable)
        last_words = self._handle_last_words(night_deaths)
        
        # Store last words in game state for context access
        self.game_state.last_words_context = last_words
        
        # 3. Day discussion
        discussion = self._day_discussion(night_deaths)
        
        # 4. Voting phase
        voting_result = self._voting_phase()
        
        # 5. Handle hunter shot if applicable
        hunter_shot = self._handle_hunter_shot(voting_result)
        
        # 6. Process all day deaths
        day_deaths = self._process_day_deaths(voting_result, hunter_shot)
        
        # Update game state
        for death in day_deaths:
            self.game_state.kill_player(death)
            self.game_state.deaths_this_day.append(death)
        
        return {
            "round": self.game_state.current_round,
            "night_deaths": night_deaths,
            "day_deaths": day_deaths,
            "death_announcement": death_announcement,
            "last_words": last_words,
            "discussion": discussion,
            "voting_result": voting_result,
            "hunter_shot": hunter_shot
        }
    
    def _announce_deaths(self, deaths: List[int]) -> Dict[str, Any]:
        """Announce deaths from the night"""
        if not deaths:
            announcement = "昨晚是平安夜，没有人死亡。"
        else:
            death_names = [self.game_state.get_player_by_id(pid).name for pid in deaths]
            announcement = f"昨晚死亡的玩家是：{', '.join(death_names)}({', '.join(map(str, deaths))})"
        
        print(f"主持人：{announcement}")
        
        return {
            "type": "death_announcement",
            "deaths": deaths,
            "announcement": announcement
        }
    
    def _handle_last_words(self, deaths: List[int]) -> List[Dict[str, Any]]:
        """Handle last words for players who died at night"""
        last_words = []
        
        if not deaths:
            return last_words
        
        # Check if last words are allowed
        has_last_words = False
        if self.game_state.current_round == 1:
            # 首夜死亡都有遗言
            has_last_words = True
        elif len(deaths) == 1:
            # 后续夜晚单人死亡有遗言
            has_last_words = True
        
        if has_last_words:
            print("接下来请死亡玩家发表遗言...")
            
            for player_id in deaths:
                player = self.game_state.get_player_by_id(player_id)
                if player:
                    context = self.game_state.get_context_for_player(player_id)
                    context["is_last_words"] = True
                    context["death_reason"] = "被狼人击杀"
                    
                    speech = player.speak(context)
                    
                    last_words.append({
                        "player": player_id,
                        "name": player.name,
                        "speech": speech,
                        "is_last_words": True
                    })
                    
                    # print(f"{player.name}的遗言：{speech}")
        else:
            print("由于多人死亡，死亡玩家无遗言")
        
        return last_words
    
    def _day_discussion(self, night_deaths: List[int]) -> List[Dict[str, Any]]:
        """Handle day discussion phase"""
        print("=== 白天讨论阶段 ===")
        
        discussion = []
        alive_players = self.game_state.get_alive_players()
        
        if not alive_players:
            return discussion
        
        # Determine speaking order (clockwise from last death or random)
        speaking_order = self._get_speaking_order(night_deaths, alive_players)
        speaking_order_ids = [p.id for p in speaking_order]
        
        for i, player in enumerate(speaking_order):
            if player.is_alive():
                # Get day-specific context with speaking order
                context = self.game_state.get_context_for_player(player.id, "day")
                context["night_deaths"] = night_deaths
                context["discussion_phase"] = "day"
                
                # Ensure speaking order is correctly set
                context["speaking_order"] = speaking_order_ids
                context["my_position"] = i + 1
                context["players_before_me"] = [
                    {"id": p.id, "name": p.name, "status": "alive" if p.is_alive() else "dead"}
                    for p in speaking_order[:i]
                ]
                context["players_after_me"] = [
                    {"id": p.id, "name": p.name, "status": "alive" if p.is_alive() else "dead"}
                    for p in speaking_order[i+1:]
                ]
                
                speech = player.speak(context)
                
                discussion.append({
                    "player": player.id,
                    "name": player.name,
                    "speech": speech,
                    "phase": "discussion",
                    "speaking_order": i + 1
                })
                
                # print(f"[{i+1}/{len(speaking_order)}] {player.name}：{speech}")
        
        return discussion
    
    def _get_speaking_order(self, night_deaths: List[int], alive_players: List) -> List:
        """Determine speaking order for day discussion"""
        if night_deaths:
            # Start from the player after the last death
            last_death = max(night_deaths)
            start_index = 0
            
            # Find the next alive player after last death
            for i, player in enumerate(alive_players):
                if player.id > last_death:
                    start_index = i
                    break
            
            # Reorder players starting from start_index
            speaking_order = alive_players[start_index:] + alive_players[:start_index]
        else:
            # If no deaths, start from player 1
            speaking_order = sorted(alive_players, key=lambda p: p.id)
        
        return speaking_order
    
    def _voting_phase(self) -> Dict[str, Any]:
        """Handle voting phase"""
        print("=== 投票阶段 ===")
        
        alive_players = self.game_state.get_alive_players()
        if len(alive_players) <= 1:
            return {"votes": {}, "eliminated": None, "reason": "玩家不足"}
        
        # Collect votes from all alive players
        votes = {}
        candidate_ids = [p.id for p in alive_players]
        
        for voter in alive_players:
            if voter.is_alive():
                context = self.game_state.get_context_for_player(voter.id)
                context["voting_phase"] = True
                context["candidates"] = candidate_ids
                
                voted_player = voter.vote_for_player(candidate_ids)
                
                if voted_player in candidate_ids:
                    votes[voter.id] = voted_player
                    self.game_state.record_vote(voter.id, voted_player)
                    
                    target_name = self.game_state.get_player_by_id(voted_player).name
                    print(f"{voter.name} 投票给了 {target_name}({voted_player})")
                else:
                    # Default to first candidate if invalid
                    votes[voter.id] = candidate_ids[0]
                    self.game_state.record_vote(voter.id, candidate_ids[0])
                    target_name = self.game_state.get_player_by_id(candidate_ids[0]).name
                    print(f"{voter.name} 投票给了 {target_name}({candidate_ids[0]}) (默认)")
        
        # Count votes
        vote_count = {}
        for voter, target in votes.items():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        # Determine eliminated player
        eliminated = None
        max_votes = max(vote_count.values()) if vote_count else 0
        most_voted = [pid for pid, votes in vote_count.items() if votes == max_votes]
        
        if len(most_voted) == 1:
            eliminated = most_voted[0]
            eliminated_player = self.game_state.get_player_by_id(eliminated)
            print(f"投票结果：{eliminated_player.name}({eliminated}) 被投票淘汰")
        else:
            print("投票结果：平票，无人被淘汰")
        
        return {
            "votes": votes,
            "vote_count": vote_count,
            "eliminated": eliminated,
            "max_votes": max_votes,
            "tie": len(most_voted) > 1
        }
    
    def _handle_hunter_shot(self, voting_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle hunter shot if hunter was eliminated"""
        eliminated = voting_result.get("eliminated")
        if not eliminated:
            return None
        
        eliminated_player = self.game_state.get_player_by_id(eliminated)
        if not eliminated_player or eliminated_player.role != Role.HUNTER:
            return None
        
        if not eliminated_player.hunter_can_shoot:
            return None
        
        print(f"猎人 {eliminated_player.name} 被投票淘汰，可以选择开枪...")
        
        alive_players = self.game_state.get_alive_players()
        target_ids = [p.id for p in alive_players]
        
        if target_ids:
            context = self.game_state.get_context_for_player(eliminated)
            context["death_reason"] = "被投票淘汰"
            context["is_hunter_shot"] = True
            context["available_targets"] = target_ids
            
            shot_target = eliminated_player.vote_for_player(target_ids, "选择开枪目标")
            
            if shot_target in target_ids:
                target_player = self.game_state.get_player_by_id(shot_target)
                print(f"猎人 {eliminated_player.name} 开枪带走了 {target_player.name}({shot_target})")
                
                return {
                    "type": "hunter_shot",
                    "hunter": eliminated,
                    "target": shot_target,
                    "successful": True
                }
        
        return {
            "type": "hunter_shot",
            "hunter": eliminated,
            "target": None,
            "successful": False
        }
    
    def _process_day_deaths(self, voting_result: Dict[str, Any], hunter_shot: Optional[Dict[str, Any]]) -> List[int]:
        """Process all deaths from day phase"""
        deaths = []
        
        # Voting elimination
        eliminated = voting_result.get("eliminated")
        if eliminated:
            deaths.append(eliminated)
        
        # Hunter shot
        if hunter_shot and hunter_shot.get("successful"):
            target = hunter_shot.get("target")
            if target and target not in deaths:
                deaths.append(target)
        
        # Handle last words for day deaths
        if deaths:
            print("=== 白天死亡玩家 ===")
            for death_id in deaths:
                player = self.game_state.get_player_by_id(death_id)
                if player:
                    print(f"{player.name}({death_id}) 被淘汰")
        
        return deaths