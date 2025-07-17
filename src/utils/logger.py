import json
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


class GameLogger:
    def __init__(self, game_id: str = None, log_dir: str = "logs"):
        self.game_id = game_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create log file paths
        self.game_log_file = self.log_dir / f"game_{self.game_id}.jsonl"
        self.conversation_log_file = self.log_dir / f"conversations_{self.game_id}.jsonl"
        self.summary_log_file = self.log_dir / f"summary_{self.game_id}.json"
        
        # Initialize log files
        self._initialize_log_files()
        
    def _initialize_log_files(self):
        """Initialize log files with headers"""
        # Game log - JSON Lines format
        with open(self.game_log_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                "type": "game_start",
                "game_id": self.game_id,
                "timestamp": datetime.now().isoformat(),
                "message": "Game started"
            }, ensure_ascii=False) + '\n')
        
        # Conversation log - JSON Lines format
        with open(self.conversation_log_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                "type": "conversation_start",
                "game_id": self.game_id,
                "timestamp": datetime.now().isoformat(),
                "message": "Conversation logging started"
            }, ensure_ascii=False) + '\n')
    
    def log_game_event(self, event_type: str, data: Dict[str, Any], round_num: int = None):
        """Log a game event"""
        log_entry = {
            "type": event_type,
            "game_id": self.game_id,
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "data": data
        }
        
        with open(self.game_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_conversation(self, player_id: int, player_name: str, message: str, 
                        context: Dict[str, Any] = None, phase: str = None):
        """Log a player conversation"""
        log_entry = {
            "type": "conversation",
            "game_id": self.game_id,
            "timestamp": datetime.now().isoformat(),
            "player_id": player_id,
            "player_name": player_name,
            "message": message,
            "phase": phase,
            "context": context or {}
        }
        
        with open(self.conversation_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_night_phase(self, round_num: int, night_results: Dict[str, Any]):
        """Log night phase results"""
        self.log_game_event("night_phase", night_results, round_num)
    
    def log_day_phase(self, round_num: int, day_results: Dict[str, Any]):
        """Log day phase results"""
        self.log_game_event("day_phase", day_results, round_num)
    
    def log_player_action(self, player_id: int, player_name: str, action: str, 
                         target: int = None, result: str = None, round_num: int = None):
        """Log a player action"""
        action_data = {
            "player_id": player_id,
            "player_name": player_name,
            "action": action,
            "target": target,
            "result": result
        }
        
        self.log_game_event("player_action", action_data, round_num)
    
    def log_vote(self, round_num: int, voter_id: int, voter_name: str, 
                target_id: int, target_name: str):
        """Log a vote"""
        vote_data = {
            "voter_id": voter_id,
            "voter_name": voter_name,
            "target_id": target_id,
            "target_name": target_name
        }
        
        self.log_game_event("vote", vote_data, round_num)
    
    def log_death(self, player_id: int, player_name: str, role: str, 
                 death_reason: str, round_num: int):
        """Log a player death"""
        death_data = {
            "player_id": player_id,
            "player_name": player_name,
            "role": role,
            "death_reason": death_reason
        }
        
        self.log_game_event("death", death_data, round_num)
    
    def log_game_end(self, winner: str, reason: str, final_state: Dict[str, Any]):
        """Log game end"""
        end_data = {
            "winner": winner,
            "reason": reason,
            "final_state": final_state,
            "duration": str(datetime.now() - 
                          datetime.fromisoformat(self._get_game_start_time()))
        }
        
        self.log_game_event("game_end", end_data)
        
        # Save summary
        summary = {
            "game_id": self.game_id,
            "start_time": self._get_game_start_time(),
            "end_time": datetime.now().isoformat(),
            "winner": winner,
            "reason": reason,
            "final_state": final_state
        }
        
        with open(self.summary_log_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    
    def _get_game_start_time(self) -> str:
        """Get game start time from log file"""
        try:
            with open(self.game_log_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line:
                    start_data = json.loads(first_line)
                    return start_data.get('timestamp', datetime.now().isoformat())
        except:
            pass
        return datetime.now().isoformat()
    
    def get_game_logs(self) -> List[Dict[str, Any]]:
        """Get all game logs"""
        logs = []
        try:
            with open(self.game_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        logs.append(json.loads(line))
        except FileNotFoundError:
            pass
        return logs
    
    def get_conversation_logs(self) -> List[Dict[str, Any]]:
        """Get all conversation logs"""
        logs = []
        try:
            with open(self.conversation_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        logs.append(json.loads(line))
        except FileNotFoundError:
            pass
        return logs
    
    def export_logs(self, format_type: str = "json", output_file: str = None) -> str:
        """Export logs in different formats"""
        if format_type == "json":
            if not output_file:
                output_file = self.log_dir / f"export_{self.game_id}.json"
            
            export_data = {
                "game_logs": self.get_game_logs(),
                "conversation_logs": self.get_conversation_logs(),
                "summary": self._get_summary()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return str(output_file)
        
        return "Unsupported format"
    
    def _get_summary(self) -> Dict[str, Any]:
        """Get game summary from summary file"""
        try:
            with open(self.summary_log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"game_id": self.game_id, "status": "in_progress"}