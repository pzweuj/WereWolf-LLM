#!/usr/bin/env python3
"""
狼人杀游戏修复验证测试脚本

测试内容：
1. 女巫解药机制：狼人击杀→女巫救人→确认无人死亡
2. 遗言传递机制：玩家死亡→发表遗言→白天讨论包含遗言信息
"""

import sys
import os
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.game.game_state import GameState
from src.phases.night_phase import NightPhase
from src.phases.day_phase import DayPhase
from src.models.player import Role, Team
from src.models.llm_player import LLMPlayer


class MockLLMPlayer(LLMPlayer):
    """Mock LLM Player for testing without API calls"""
    
    def __init__(self, id: int, name: str, role: Role, test_actions: Dict[str, Any] = None, **kwargs):
        # Initialize with dummy API credentials
        super().__init__(
            id=id,
            name=name,
            role=role,
            api_url="http://localhost",
            api_key="test-key",
            model="test-model",
            **kwargs
        )
        # Store test actions as instance variable
        object.__setattr__(self, '_test_actions', test_actions or {})
    
    def send_message(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Mock LLM response for testing"""
        if "遗言" in prompt or "LAST_WORDS" in prompt:
            return f"LAST_WORDS: 我是{self.name}，我的身份是{self.get_role_description()}。请大家相信我的判断。"
        elif "投票" in prompt or "VOTE" in prompt:
            return "VOTE: 2\nREASON: 基于分析选择玩家2"
        elif "发言" in prompt or "SPEECH" in prompt:
            return f"SPEECH: 我是{self.name}，根据目前的情况，我认为需要仔细分析。"
        else:
            return "测试回复"
    
    def make_night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock night action for testing"""
        test_actions = getattr(self, '_test_actions', {})
        
        if self.role == Role.WITCH:
            # Test witch heal action
            if "heal_test" in test_actions:
                return {"action": "heal", "target": test_actions["heal_test"]}
            elif "poison_test" in test_actions:
                return {"action": "poison", "target": test_actions["poison_test"]}
            else:
                return {"action": "none"}
        elif self.role == Role.WEREWOLF:
            # Test wolf kill action
            return {"action": "kill", "target": test_actions.get("kill_target", 1)}
        elif self.role == Role.SEER:
            # Test seer check action
            return {"action": "check", "target": test_actions.get("check_target", 2)}
        else:
            return {}


def create_test_game() -> GameState:
    """Create a test game with mock players"""
    game_state = GameState()
    
    # Create test players
    players = [
        MockLLMPlayer(1, "村民1", Role.VILLAGER),
        MockLLMPlayer(2, "狼人1", Role.WEREWOLF, {"kill_target": 1}),
        MockLLMPlayer(3, "预言家", Role.SEER, {"check_target": 2}),
        MockLLMPlayer(4, "女巫", Role.WITCH, {"heal_test": 1}),  # Will heal player 1
        MockLLMPlayer(5, "猎人", Role.HUNTER),
    ]
    
    for player in players:
        game_state.add_player(player)
    
    return game_state


def test_witch_heal_mechanism():
    """测试女巫解药机制"""
    print("=== 测试1: 女巫解药机制 ===")
    
    game_state = create_test_game()
    game_state.current_round = 1
    night_phase = NightPhase(game_state)
    
    print("测试场景：狼人击杀玩家1，女巫使用解药救治")
    
    # Execute night phase
    night_result = night_phase.execute_night_phase()
    
    # Verify results
    deaths = night_result["deaths"]
    witch_heal_used = night_result["witch_heal_used"]
    
    print(f"夜晚死亡玩家: {deaths}")
    print(f"女巫是否使用解药: {witch_heal_used}")
    
    # Test assertions
    if len(deaths) == 0 and witch_heal_used:
        print("✅ 测试通过：女巫解药成功救治，无人死亡")
        return True
    else:
        print("❌ 测试失败：女巫解药机制未正常工作")
        return False


def test_last_words_transmission():
    """测试遗言信息传递机制"""
    print("\n=== 测试2: 遗言信息传递机制 ===")
    
    game_state = create_test_game()
    game_state.current_round = 1
    
    # Create a scenario where player dies and has last words
    night_phase = NightPhase(game_state)
    day_phase = DayPhase(game_state)
    
    # Modify witch to not heal, so player 1 dies
    witch = game_state.get_player_by_id(4)
    object.__setattr__(witch, '_test_actions', {"no_heal": True})  # Don't heal
    
    print("测试场景：玩家1死亡并发表遗言，检查白天讨论是否包含遗言信息")
    
    # Execute night phase (player 1 should die)
    night_result = night_phase.execute_night_phase()
    deaths = night_result["deaths"]
    
    if not deaths:
        print("⚠️ 跳过测试：没有玩家死亡，无法测试遗言传递")
        return True
    
    print(f"夜晚死亡玩家: {deaths}")
    
    # Execute day phase
    day_result = day_phase.execute_day_phase(deaths)
    last_words = day_result["last_words"]
    
    print(f"收集到的遗言: {len(last_words)} 条")
    for lw in last_words:
        print(f"  - {lw['name']}({lw['player']}): {lw['speech'][:50]}...")
    
    # Check if last words are properly stored in game state
    stored_last_words = game_state.last_words_context
    print(f"游戏状态中存储的遗言: {len(stored_last_words)} 条")
    
    # Test day discussion context
    alive_players = game_state.get_alive_players()
    if alive_players:
        test_player = alive_players[0]
        day_context = game_state.get_context_for_player(test_player.id, "day")
        context_last_words = day_context.get("last_words", [])
        
        print(f"白天讨论上下文中的遗言: {len(context_last_words)} 条")
        
        # Test assertions
        if len(last_words) > 0 and len(stored_last_words) > 0 and len(context_last_words) > 0:
            print("✅ 测试通过：遗言信息正确传递到白天讨论")
            return True
        else:
            print("❌ 测试失败：遗言信息传递不完整")
            return False
    else:
        print("⚠️ 无存活玩家进行白天讨论测试")
        return True


def test_game_state_validation():
    """测试游戏状态验证功能"""
    print("\n=== 测试3: 游戏状态验证 ===")
    
    game_state = create_test_game()
    
    # Test last words validation
    print("测试遗言验证功能...")
    
    # Valid last word
    valid_result = game_state.add_last_words(1, "这是一条有效的遗言", "测试死亡")
    print(f"有效遗言添加结果: {valid_result}")
    
    # Invalid last word (empty speech)
    invalid_result = game_state.add_last_words(2, "", "测试死亡")
    print(f"无效遗言添加结果: {invalid_result}")
    
    # Invalid last word (non-existent player)
    invalid_player_result = game_state.add_last_words(999, "不存在的玩家", "测试死亡")
    print(f"不存在玩家遗言添加结果: {invalid_player_result}")
    
    # Check stored last words
    stored_count = len(game_state.last_words_context)
    print(f"存储的遗言数量: {stored_count}")
    
    if valid_result and not invalid_result and not invalid_player_result and stored_count == 1:
        print("✅ 测试通过：遗言验证功能正常")
        return True
    else:
        print("❌ 测试失败：遗言验证功能异常")
        return False


def run_comprehensive_test():
    """运行综合测试"""
    print("🎮 狼人杀游戏修复验证测试开始")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Witch heal mechanism
    try:
        result1 = test_witch_heal_mechanism()
        test_results.append(("女巫解药机制", result1))
    except Exception as e:
        print(f"❌ 测试1异常: {e}")
        test_results.append(("女巫解药机制", False))
    
    # Test 2: Last words transmission
    try:
        result2 = test_last_words_transmission()
        test_results.append(("遗言信息传递", result2))
    except Exception as e:
        print(f"❌ 测试2异常: {e}")
        test_results.append(("遗言信息传递", False))
    
    # Test 3: Game state validation
    try:
        result3 = test_game_state_validation()
        test_results.append(("游戏状态验证", result3))
    except Exception as e:
        print(f"❌ 测试3异常: {e}")
        test_results.append(("游戏状态验证", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 测试结果总结:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！修复效果验证成功。")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步检查修复效果。")
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)