import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.game.game_manager import GameManager


def load_game_config(config_file: str) -> dict:
    """Load game configuration from JSON file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件 {config_file} 未找到")
        return None
    except json.JSONDecodeError:
        print(f"配置文件 {config_file} 格式错误")
        return None


def create_sample_config():
    """Create a sample configuration file"""
    config = {
        "players": [
            {"id": 1, "name": "狼人1", "role": "werewolf", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-1"},
            {"id": 2, "name": "狼人2", "role": "werewolf", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-2"},
            {"id": 3, "name": "狼人3", "role": "werewolf", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-3"},
            {"id": 4, "name": "预言家", "role": "seer", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-4"},
            {"id": 5, "name": "女巫", "role": "witch", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-5"},
            {"id": 6, "name": "猎人", "role": "hunter", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-6"},
            {"id": 7, "name": "村民1", "role": "villager", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-7"},
            {"id": 8, "name": "村民2", "role": "villager", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-8"},
            {"id": 9, "name": "村民3", "role": "villager", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-9"},
            {"id": 10, "name": "村民4", "role": "villager", "api_url": "https://api.openai.com/v1", "api_key": "sk-your-key-10"}
        ]
    }
    
    with open("game_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("已创建示例配置文件：game_config.json")
    print("请修改配置文件中的API密钥和URL，然后运行游戏")


def main():
    """Main game runner"""
    print("=== 狼人杀LLM游戏 ===")
    
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "game_config.json"
    
    # Check if config file exists
    if not Path(config_file).exists():
        print(f"配置文件 {config_file} 不存在")
        create_choice = input("是否创建示例配置文件？(y/n): ").strip().lower()
        if create_choice == 'y':
            create_sample_config()
            return
        else:
            print("请提供配置文件路径作为参数，例如: python main.py your_config.json")
            return
    
    # Load configuration
    config = load_game_config(config_file)
    if not config:
        return
    
    # Create and start game
    game_manager = GameManager()
    
    # Setup game
    if not game_manager.setup_game(config["players"]):
        print("游戏设置失败")
        return
    
    # Start game
    try:
        result = game_manager.start_game()
        print("\n游戏完成！")
        print(f"游戏ID: {result['game_id']}")
        print(f"胜利方: {result['winner']}")
        print(f"原因: {result['reason']}")
        
    except KeyboardInterrupt:
        print("\n游戏被中断")
    except Exception as e:
        print(f"游戏运行时出错: {e}")


if __name__ == "__main__":
    main()