#!/usr/bin/env python3
"""
Test script to verify the werewolf game setup
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_imports():
    """Test if all modules can be imported correctly"""
    print("测试模块导入...")
    
    try:
        from src.models.player import Player, Role
        from src.models.llm_player import LLMPlayer
        from src.game.game_state import GameState
        from src.phases.night_phase import NightPhase
        from src.phases.day_phase import DayPhase
        from src.utils.logger import GameLogger
        from src.game.game_manager import GameManager
        
        print("所有模块导入成功")
        return True
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_basic_functionality():
    """Test basic game functionality"""
    print("测试基础功能...")
    
    try:
        # Test player creation
        from src.models.player import Player, Role
        player = Player(id=1, name="TestPlayer", role=Role.WEREWOLF, 
                       api_url="http://test.com", api_key="test")
        print(f"玩家创建成功: {player.name} - {player.role.value}")
        
        # Test game state
        from src.game.game_state import GameState
        game_state = GameState()
        game_state.add_player(player)
        print(f"游戏状态创建成功: {len(game_state.players)} 个玩家")
        
        # Test logger
        from src.utils.logger import GameLogger
        logger = GameLogger("test")
        logger.log_game_event("test", {"message": "测试日志"})
        print("日志系统工作正常")
        
        return True
    except Exception as e:
        print(f"基础功能测试失败: {e}")
        return False

def test_game_setup():
    """Test game setup with sample configuration"""
    print("测试游戏设置...")
    
    try:
        from src.game.game_manager import GameManager
        
        # Create sample configuration
        players_config = [
            {"id": i, "name": f"玩家{i}", "role": "villager", 
             "api_url": "http://test.com", "api_key": "test"}
            for i in range(1, 11)
        ]
        
        # Override some roles for proper setup
        players_config[0]["role"] = "werewolf"
        players_config[1]["role"] = "werewolf"
        players_config[2]["role"] = "werewolf"
        players_config[3]["role"] = "seer"
        players_config[4]["role"] = "witch"
        players_config[5]["role"] = "hunter"
        
        game_manager = GameManager()
        success = game_manager.setup_game(players_config)
        
        if success:
            print("游戏设置成功")
            return True
        else:
            print("游戏设置失败")
            return False
            
    except Exception as e:
        print(f"游戏设置测试失败: {e}")
        return False

def main():
    """Run all tests"""
    print("=== 狼人杀游戏设置测试 ===\n")
    
    tests = [
        test_imports,
        test_basic_functionality,
        test_game_setup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("所有测试通过！游戏设置成功")
        print("\n下一步：")
        print("1. 修改 game_config.json 文件，添加真实的API密钥")
        print("2. 运行: python main.py")
        print("3. 或者运行: python main.py game_config.json")
    else:
        print("部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()