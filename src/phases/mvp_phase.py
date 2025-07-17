from typing import List, Dict, Any
from ..models.player import Player, Role
from ..game.game_state import GameState


class MVPPhase:
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def execute_mvp_voting(self) -> Dict[str, Any]:
        """Execute MVP voting after game ends"""
        print("\n=== MVP投票阶段 ===")
        print("所有存活和已死亡的玩家将投票选出本局游戏的MVP")
        
        all_players = self.game_state.players
        alive_players = [p for p in all_players if p.is_alive()]
        dead_players = [p for p in all_players if not p.is_alive()]
        
        # Available candidates are all players
        candidates = [p.id for p in all_players]
        candidate_names = {p.id: p.name for p in all_players}
        
        # Collect votes from all players
        votes = {}
        vote_explanations = {}
        
        for voter in all_players:
            context = {
                "game_summary": self._get_game_summary_for_mvp(),
                "candidates": candidates,
                "voter_role": voter.role.value,
                "voter_name": voter.name,
                "is_mvp_voting": True
            }
            
            prompt = f"""
            游戏已经结束，请投票选出本局游戏的MVP（最有价值玩家）。
            
            候选玩家：{[f'{pid}: {candidate_names[pid]}' for pid in candidates]}
            
            请考虑以下因素：
            1. 玩家的策略和表现
            2. 对游戏结果的影响
            3. 发言和推理的质量
            4. 角色扮演的精彩程度
            
            请直接回复你要投票的玩家ID（1-10之间的数字），并简要说明理由。
            """
            
            response = voter.send_message(prompt, context)
            
            # Parse vote from response
            import re
            numbers = re.findall(r'\d+', response)
            voted_id = None
            
            for num_str in numbers:
                try:
                    num = int(num_str)
                    if num in candidates:
                        voted_id = num
                        break
                except ValueError:
                    continue
            
            if voted_id is None:
                # Default to first candidate if no valid vote
                voted_id = candidates[0]
            
            votes[voter.id] = voted_id
            vote_explanations[voter.id] = {
                "voter_name": voter.name,
                "voted_for": voted_id,
                "voted_for_name": candidate_names[voted_id],
                "explanation": response,
                "role": voter.role.value
            }
            
            print(f"{voter.name}({voter.role.value})投票给了{candidate_names[voted_id]}: {response[:100]}...")
        
        # Count votes
        vote_count = {}
        for voter_id, target_id in votes.items():
            vote_count[target_id] = vote_count.get(target_id, 0) + 1
        
        # Determine MVP
        max_votes = max(vote_count.values()) if vote_count else 0
        mvps = [pid for pid, votes in vote_count.items() if votes == max_votes]
        
        if len(mvps) == 1:
            mvp_id = mvps[0]
            mvp_player = next(p for p in all_players if p.id == mvp_id)
            mvp_name = mvp_player.name
            mvp_role = mvp_player.role.value
            is_tie = False
        else:
            # In case of tie, choose the first one
            mvp_id = mvps[0]
            mvp_player = next(p for p in all_players if p.id == mvp_id)
            mvp_name = mvp_player.name
            mvp_role = mvp_player.role.value
            is_tie = True
        
        # Calculate vote percentages
        total_votes = len(votes)
        vote_percentages = {
            pid: (count / total_votes) * 100 
            for pid, count in vote_count.items()
        }
        
        result = {
            "mvp": {
                "id": mvp_id,
                "name": mvp_name,
                "role": mvp_role,
                "votes": vote_count.get(mvp_id, 0),
                "percentage": vote_percentages.get(mvp_id, 0)
            },
            "vote_count": vote_count,
            "vote_percentages": vote_percentages,
            "vote_explanations": vote_explanations,
            "total_voters": total_votes,
            "is_tie": is_tie
        }
        
        if is_tie:
            print(f"\n平局！多个玩家获得最高票数")
        
        print(f"\n=== MVP结果 ===")
        print(f"本局MVP: {mvp_name}({mvp_role}) - {vote_count.get(mvp_id, 0)}票 ({vote_percentages.get(mvp_id, 0):.1f}%)")
        
        print("\n投票详情:")
        for voter_id, vote_info in vote_explanations.items():
            print(f"{vote_info['voter_name']}({vote_info['role']}) → {vote_info['voted_for_name']}")
        
        return result
    
    def _get_game_summary_for_mvp(self) -> str:
        """Get game summary for MVP voting"""
        all_players = self.game_state.players
        alive_players = [p for p in all_players if p.is_alive()]
        dead_players = [p for p in all_players if not p.is_alive()]
        
        summary = f"""
        游戏总结：
        总回合数: {self.game_state.current_round}
        存活玩家: {len(alive_players)}人
        死亡玩家: {len(dead_players)}人
        
        死亡玩家详情：
        """
        
        for player in dead_players:
            summary += f"- {player.name} ({player.role.value})\n"
        
        summary += f"\n存活玩家：\n"
        for player in alive_players:
            summary += f"- {player.name} ({player.role.value})\n"
        
        return summary