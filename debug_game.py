#!/usr/bin/env python3
"""
Debug script to identify the 'witch' error
"""
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.game.game_manager import GameManager
from src.models.player import Role

def debug_config(config_file: str):
    """Debug the configuration and identify the witch error"""
    print(f"=== Debugging {config_file} ===")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("Configuration loaded successfully")
        print(f"Number of players: {len(config['players'])}")
        
        # Check roles
        roles = [p["role"] for p in config["players"]]
        print(f"Roles: {roles}")
        
        # Check role counts
        role_counts = {
            "werewolf": roles.count("werewolf"),
            "seer": roles.count("seer"),
            "witch": roles.count("witch"),
            "hunter": roles.count("hunter"),
            "villager": roles.count("villager")
        }
        print(f"Role counts: {role_counts}")
        
        # Test role enum conversion
        for i, player_config in enumerate(config["players"]):
            try:
                role = Role(player_config["role"])
                print(f"Player {i+1}: {player_config['name']} -> {role} (type: {type(role)})")
            except Exception as e:
                print(f"Error converting role for player {i+1}: {e}")
        
        # Try to create game manager
        print("\n=== Testing Game Setup ===")
        game_manager = GameManager()
        
        # Test setup
        setup_result = game_manager.setup_game(config["players"])
        print(f"Setup result: {setup_result}")
        
        if setup_result:
            print("Game setup successful!")
            # Print players with debug info
            for player in game_manager.game_state.players:
                print(f"Player {player.id}: {player.name} - {player.role} (type: {type(player.role)}) - {player.team}")
                print(f"  Role comparison: {player.role} == {Role.WEREWOLF} -> {player.role == Role.WEREWOLF}")
                print(f"  Str role: '{str(player.role)}'")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "config/my_config_ran.json"
    
    debug_config(config_file)