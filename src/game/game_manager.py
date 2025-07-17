import json
from typing import List, Dict, Any
from datetime import datetime

from ..models.player import Player, Role
from ..models.llm_player import LLMPlayer
from ..game.game_state import GameState
from ..phases.night_phase import NightPhase
from ..phases.day_phase import DayPhase
from ..phases.mvp_phase import MVPPhase
from ..utils.logger import GameLogger


class GameManager:
    def __init__(self, game_id: str = None):
        self.game_state = GameState()
        self.night_phase = NightPhase(self.game_state)
        self.day_phase = DayPhase(self.game_state)
        self.mvp_phase = MVPPhase(self.game_state)
        self.logger = GameLogger(game_id)
        
    def setup_game(self, players_config: List[Dict[str, Any]]) -> bool:
        """Setup the game with player configurations"""
        try:
            # Validate player count (should be 10)
            if len(players_config) != 10:
                print("错误：游戏需要10个玩家")
                return False
            
            # Validate roles
            roles = [p["role"] for p in players_config]
            role_counts = {
                "werewolf": roles.count("werewolf"),
                "seer": roles.count("seer"),
                "witch": roles.count("witch"),
                "hunter": roles.count("hunter"),
                "villager": roles.count("villager")
            }
            
            expected_counts = {
                "werewolf": 3,
                "seer": 1,
                "witch": 1,
                "hunter": 1,
                "villager": 4
            }
            
            if role_counts != expected_counts:
                print(f"错误：角色配置不正确。期望：{expected_counts}，实际：{role_counts}")
                return False
            
            # Create players
            for i, config in enumerate(players_config, 1):
                player = LLMPlayer(
                    id=i,
                    name=config["name"],
                    role=Role(config["role"]),
                    api_url=config["api_url"],
                    api_key=config["api_key"],
                    model=config.get("model", "gpt-3.5-turbo")
                )
                self.game_state.add_player(player)
                
                self.logger.log_game_event("player_added", {
                    "player_id": i,
                    "name": config["name"],
                    "role": config["role"]
                })
            
            self.logger.log_game_event("game_setup", {
                "total_players": len(players_config),
                "roles": role_counts
            })
            
            return True
            
        except Exception as e:
            print(f"设置游戏时出错：{e}")
            return False
    
    def start_game(self) -> Dict[str, Any]:
        """Start and run the complete game"""
        print("=== 狼人杀游戏开始 ===")
        print(f"游戏ID：{self.logger.game_id}")
        
        # Announce player roles
        self._announce_players()
        
        # Game loop
        while True:
            self.game_state.current_round += 1
            
            print(f"\n=== 第{self.game_state.current_round}轮 ===")
            
            # Night phase
            self.game_state.phase = "night"
            night_results = self.night_phase.execute_night_phase()
            
            self.logger.log_night_phase(self.game_state.current_round, night_results)
            
            # Check victory conditions after night
            victory_check = self.game_state.check_victory_conditions()
            if victory_check["game_over"]:
                return self._end_game(victory_check)
            
            # Day phase
            self.game_state.phase = "day"
            day_results = self.day_phase.execute_day_phase(night_results["deaths"])
            
            self.logger.log_day_phase(self.game_state.current_round, day_results)
            
            # Check victory conditions after day
            victory_check = self.game_state.check_victory_conditions()
            if victory_check["game_over"]:
                return self._end_game(victory_check)
            
            # Log deaths
            all_deaths = night_results["deaths"] + day_results["day_deaths"]
            for death_id in all_deaths:
                player = self.game_state.get_player_by_id(death_id)
                if player:
                    self.logger.log_death(
                        death_id, player.name, player.role.value,
                        "游戏进行中", self.game_state.current_round
                    )
            
            # Show current state
            self._show_current_state()
        
    def _announce_players(self):
        """Announce all players and their initial state"""
        print("\n=== 玩家列表 ===")
        for player in self.game_state.players:
            print(f"{player.id}. {player.name} - {player.get_role_description()}")
        print()
    
    def _show_current_state(self):
        """Show current game state"""
        summary = self.game_state.get_game_summary()
        
        print("\n当前游戏状态：")
        print(f"回合：{summary['round']}")
        print(f"存活玩家：{len(summary['alive_players'])}")
        print(f"死亡玩家：{len(summary['dead_players'])}")
        print(f"存活狼人：{summary['alive_wolves']}")
        print(f"存活好人：{summary['alive_villagers']}")
        
        alive_names = [p['name'] for p in summary['alive_players']]
        print(f"存活玩家：{', '.join(alive_names)}")
        
        if summary['dead_players']:
            dead_info = [f"{p['name']}({p['role']})" for p in summary['dead_players']]
            print(f"死亡玩家：{', '.join(dead_info)}")
    
    def _end_game(self, victory_check: Dict[str, Any]) -> Dict[str, Any]:
        """End the game and return final results"""
        print("\n=== 游戏结束 ===")
        print(f"胜利方：{victory_check['winner']}")
        print(f"原因：{victory_check['reason']}")
        
        # Final game state
        final_state = self.game_state.get_game_summary()
        
        # Log final deaths
        for player in self.game_state.players:
            if not player.is_alive():
                self.logger.log_death(
                    player.id, player.name, player.role.value,
                    victory_check['reason'], self.game_state.current_round
                )
        
        # MVP voting
        print("\n现在开始MVP投票...")
        mvp_result = self.mvp_phase.execute_mvp_voting()
        
        # Log MVP voting
        self.logger.log_game_event("mvp_voting", mvp_result)
        
        # Log game end
        final_state = self.game_state.get_game_summary()
        final_state["mvp"] = mvp_result["mvp"]
        
        self.logger.log_game_end(
            victory_check['winner'],
            victory_check['reason'],
            final_state
        )
        
        # Export logs
        export_file = self.logger.export_logs()
        print(f"游戏日志已保存到：{export_file}")
        
        return {
            "game_id": self.logger.game_id,
            "winner": victory_check['winner'],
            "reason": victory_check['reason'],
            "final_state": final_state,
            "mvp": mvp_result,
            "log_files": {
                "game_log": str(self.logger.game_log_file),
                "conversation_log": str(self.logger.conversation_log_file),
                "summary_log": str(self.logger.summary_log_file)
            }
        }
    
    def get_game_config_template(self) -> Dict[str, Any]:
        """Get template for game configuration from JSON file"""
        import json
        from pathlib import Path
        
        template_file = Path("config/game_config_template.json")
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"读取模板文件失败: {e}")
        
        # Fallback to basic template if file doesn't exist
        return {
            "players": [
                {"id": i, "name": f"玩家{i}", "role": "villager", 
                 "api_url": "https://api.openai.com/v1", "api_key": "your-api-key-here"}
                for i in range(1, 11)
            ]
        }