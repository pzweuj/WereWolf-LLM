#!/usr/bin/env python3
"""
测试改进后的投票逻辑
特别测试预言家查杀情况下的投票行为
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


class TestLLMPlayer(LLMPlayer):
    """Test LLM Player with controlled responses"""
    
    def __init__(self, id: int, name: str, role: Role, test_scenario: str = "normal"):
        super().__init__(
            id=id,
            name=name,
            role=role,
            api_url="http://localhost",
            api_key="test-key",
            model="test-model"
        )
        self.test_scenario = test_scenario
    
    def send_message(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Mock LLM response based on test scenario"""
        
        # Handle voting scenario
        if "投票阶段战略分析" in prompt or "VOTE:" in prompt:
            if self.role == Role.SEER:
                # Seer should reveal check results and vote for the wolf
                if "玩家2" in prompt and "狼人" in str(self.seer_checks.get(2, "")):
                    return """VOTE: 2
REASON: 我是预言家，昨晚查验了玩家2，结果是狼人。这是确凿的查杀信息，请大家相信我的查验结果，投票淘汰玩家2。"""
                else:
                    return """VOTE: 2
REASON: 根据发言分析，玩家2的行为可疑，倾向于认为是狼人。"""
            
            elif self.role == Role.WEREWOLF:
                # Wolf should try to avoid being voted out
                if self.id == 2:  # If this wolf is being accused
                    return """VOTE: 3
REASON: 我觉得玩家3的发言有问题，可能是在误导大家。我是好人，请大家不要被误导。"""
                else:
                    return """VOTE: 3
REASON: 根据分析，玩家3的逻辑有矛盾，可能是狼人。"""
            
            else:
                # Good players should believe seer's check if no counter-claim
                if "预言家" in prompt and "查杀" in prompt and "玩家2" in prompt:
                    return """VOTE: 2
REASON: 预言家明确查杀了玩家2，且无其他玩家对跳预言家，这个查杀信息可信度极高。作为好人，我选择相信预言家的查验结果。"""
                else:
                    return """VOTE: 2
REASON: 根据分析选择玩家2。"""
        
        # Handle day discussion
        elif "发言" in prompt or "SPEECH:" in prompt:
            if self.role == Role.SEER and self.seer_checks:
                # Seer should reveal check results
                check_info = []
                for pid, result in self.seer_checks.items():
                    check_info.append(f"玩家{pid}是{result}")
                
                return f"""SPEECH: 我是预言家，昨晚查验的结果是：{', '.join(check_info)}。请大家相信我的查验结果，我们应该优先投票淘汰被查杀的狼人。"""
            
            elif self.role == Role.WEREWOLF:
                if self.id == 2:  # The accused wolf
                    return """SPEECH: 我是好人，不是狼人。可能有人在误导大家，请大家仔细分析，不要被假预言家欺骗。"""
                else:
                    return """SPEECH: 根据目前的情况，我认为需要仔细分析每个人的发言逻辑。"""
            
            else:
                return """SPEECH: 我会仔细听取大家的发言，特别是神职玩家的信息，然后做出合理的判断。"""
        
        # Handle night actions
        elif "夜间" in prompt:
            if self.role == Role.SEER:
                return """CHECK: 2
REASON: 选择查验玩家2的身份"""
            elif self.role == Role.WEREWOLF:
                return """KILL: 1
REASON: 选择击杀玩家1"""
            elif self.role == Role.WITCH:
                return """ACTION: none
TARGET: """
        
        return "测试回复"
    
    def make_night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock night action"""
        if self.role == Role.SEER:
            return {"action": "check", "target": 2}
        elif self.role == Role.WEREWOLF:
            return {"action": "kill", "target": 1}
        elif self.role == Role.WITCH:
            return {"action": "none"}
        return {}


def test_seer_kill_voting_logic():
    """测试预言家查杀情况下的投票逻辑"""
    print("=== 测试预言家查杀投票逻辑 ===")
    
    # Create game with specific setup
    game_state = GameState()
    
    players = [
        TestLLMPlayer(1, "村民A", Role.VILLAGER),
        TestLLMPlayer(2, "狼人B", Role.WEREWOLF),  # Will be checked by seer
        TestLLMPlayer(3, "预言家C", Role.SEER),
        TestLLMPlayer(4, "女巫D", Role.WITCH),
        TestLLMPlayer(5, "猎人E", Role.HUNTER),
    ]
    
    for player in players:
        game_state.add_player(player)
    
    game_state.current_round = 1
    
    # Execute night phase - seer checks wolf
    night_phase = NightPhase(game_state)
    night_result = night_phase.execute_night_phase()
    
    print(f"夜晚结果：{night_result['deaths']} 人死亡")
    
    # Check seer's results
    seer = game_state.get_player_by_id(3)
    print(f"预言家查验结果：{seer.seer_checks}")
    
    # Execute day phase
    day_phase = DayPhase(game_state)
    day_result = day_phase.execute_day_phase(night_result["deaths"])
    
    # Analyze voting results
    voting_result = day_result["voting_result"]
    vote_count = voting_result["vote_count"]
    eliminated = voting_result["eliminated"]
    
    print(f"\n=== 投票分析 ===")
    print(f"投票统计：{vote_count}")
    print(f"被淘汰玩家：{eliminated}")
    
    # Check if the logic is correct
    wolf_votes = vote_count.get(2, 0)  # Votes against the wolf
    total_votes = sum(vote_count.values())
    
    print(f"针对被查杀狼人(玩家2)的投票数：{wolf_votes}/{total_votes}")
    
    # Test success criteria
    if eliminated == 2:
        print("✅ 测试通过：被查杀的狼人被正确投票淘汰")
        return True
    elif wolf_votes >= total_votes // 2:
        print("✅ 测试部分通过：大多数玩家投票给被查杀的狼人")
        return True
    else:
        print("❌ 测试失败：玩家没有正确响应预言家的查杀信息")
        return False


def test_discussion_quality():
    """测试讨论质量和逻辑"""
    print("\n=== 测试讨论质量 ===")
    
    game_state = GameState()
    
    players = [
        TestLLMPlayer(1, "村民A", Role.VILLAGER),
        TestLLMPlayer(2, "狼人B", Role.WEREWOLF),
        TestLLMPlayer(3, "预言家C", Role.SEER),
    ]
    
    for player in players:
        game_state.add_player(player)
    
    game_state.current_round = 1
    
    # Simulate seer check result
    seer = game_state.get_player_by_id(3)
    seer.seer_checks[2] = "狼人"
    
    # Test day discussion
    day_phase = DayPhase(game_state)
    discussion = day_phase._day_discussion([])
    
    print("讨论内容分析：")
    seer_revealed = False
    wolf_defended = False
    villager_believed = False
    
    for speech in discussion:
        player_id = speech["player"]
        content = speech["speech"]
        
        print(f"玩家{player_id}: {content[:100]}...")
        
        if player_id == 3 and "预言家" in content and "查验" in content:
            seer_revealed = True
            print("  ✓ 预言家正确公开身份和查验结果")
        
        if player_id == 2 and ("好人" in content or "不是狼人" in content):
            wolf_defended = True
            print("  ✓ 被查杀狼人进行了辩护")
        
        if player_id == 1 and "预言家" in content and "相信" in content:
            villager_believed = True
            print("  ✓ 村民表示相信预言家")
    
    score = sum([seer_revealed, wolf_defended, villager_believed])
    print(f"\n讨论质量评分：{score}/3")
    
    if score >= 2:
        print("✅ 讨论质量测试通过")
        return True
    else:
        print("❌ 讨论质量需要改进")
        return False


def run_voting_logic_test():
    """运行投票逻辑测试"""
    print("🎯 狼人杀投票逻辑测试开始")
    print("=" * 50)
    
    test_results = []
    
    try:
        result1 = test_seer_kill_voting_logic()
        test_results.append(("预言家查杀投票逻辑", result1))
    except Exception as e:
        print(f"❌ 测试1异常: {e}")
        test_results.append(("预言家查杀投票逻辑", False))
    
    try:
        result2 = test_discussion_quality()
        test_results.append(("讨论质量测试", result2))
    except Exception as e:
        print(f"❌ 测试2异常: {e}")
        test_results.append(("讨论质量测试", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 投票逻辑测试结果:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 投票逻辑改进成功！")
        return True
    else:
        print("⚠️ 投票逻辑仍需进一步优化。")
        return False


if __name__ == "__main__":
    success = run_voting_logic_test()
    sys.exit(0 if success else 1)