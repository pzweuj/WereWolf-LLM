import json
import sys
from pathlib import Path

def validate_config(config_file: str) -> bool:
    """Validate game configuration file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check if players key exists
        if "players" not in config:
            print("错误：配置文件缺少 'players' 键")
            return False
        
        players = config["players"]
        
        # Check player count
        if len(players) != 10:
            print(f"错误：玩家数量必须是10个，当前有{len(players)}个")
            return False
        
        # Check roles
        roles = [p.get("role") for p in players]
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
            print("错误：角色配置不正确")
            print(f"期望: {expected_counts}")
            print(f"实际: {role_counts}")
            return False
        
        # Check required fields for each player
        required_fields = ["id", "name", "role", "api_url", "api_key", "model"]
        for i, player in enumerate(players, 1):
            for field in required_fields:
                if field not in player:
                    print(f"错误：玩家{i}缺少字段 '{field}'")
                    return False
        
        # Check unique IDs
        ids = [p["id"] for p in players]
        if len(set(ids)) != len(ids):
            print("错误：玩家ID必须唯一")
            return False
        
        if set(ids) != set(range(1, 11)):
            print("错误：玩家ID必须是1-10的连续数字")
            return False
        
        print("配置文件验证通过！")
        return True
        
    except FileNotFoundError:
        print(f"错误：文件 {config_file} 不存在")
        return False
    except json.JSONDecodeError as e:
        print(f"错误：JSON格式错误 - {e}")
        return False
    except Exception as e:
        print(f"错误：{e}")
        return False

def main():
    """Command line interface for config validation"""
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "game_config.json"
    
    if validate_config(config_file):
        print(f"\n使用命令运行游戏：")
        print(f"python main.py {config_file}")
    else:
        print(f"\n请检查配置文件 {config_file}")

if __name__ == "__main__":
    main()