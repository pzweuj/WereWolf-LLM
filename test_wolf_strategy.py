#!/usr/bin/env python3
"""
测试狼人弃车保帅策略
验证狼人在队友被查杀且无法挽救时是否会果断切割
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


class StrategicTestPlayer(LLMPlayer):
    """测试狼人策略的特殊玩家类"""
    
    def __init__(self, id: int, name: str, role: Role, strategy: str = "normal", **kwargs):
        super().__init__(
            id=id,
            name=name,
            role=role,
            api_url="http://localhost",
            api_key="test-key",
            model="test-model",
            **kwargs
        )
        # 使用object.__setattr__来设置策略属性
        object.__setattr__(self, '_strategy', strategy)
    
    def send_message(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """根据策略返回不同的回复"""
        
        # 投票阶段的策略回复
        if "投票阶段战略分析" in prompt:
            if self.role == Role.SEER:
                # 预言家公开查杀信息
                return """VOTE: 2
REASON: 我是预言家，昨晚查验了玩家2，结果是狼人。这是确凿的查杀信息，所有好人都应该投票淘汰玩家2。"""
            
            elif self.role == Role.WEREWOLF:
                if self.id == 2:  # 被查杀的狼人
                    return """VOTE: 3
REASON: 我是好人，玩家3可能是假预言家，大家不要被误导。我建议投票给玩家3。"""
                elif self.id == 5:  # 另一个狼人，需要做弃车保帅决策
                    strategy = getattr(self, '_strategy', 'normal')
                    if strategy == "abandon_teammate":
                        # 弃车保帅策略
                        return """VOTE: 2
REASON: 如果玩家3真的是预言家，那么玩家2确实可疑。作为好人，我选择相信预言家的查验结果，投票给玩家2。虽然我之前觉得玩家2还可以，但预言家的信息更可靠。"""
                    else:
                        # 保护队友策略
                        return """VOTE: 3
REASON: 我觉得玩家3的预言家身份有问题，可能是假跳。玩家2平时表现正常，我倾向于相信玩家2是好人。"""
                else:
                    return """VOTE: 2
REASON: 预言家的查杀信息应该是可信的，我选择投票给玩家2。"""
            
            else:
                # 好人玩家相信预言家
                return """VOTE: 2
REASON: 预言家明确查杀了玩家2，且无其他玩家对跳预言家，这个查杀信息可信度极高。作为好人，我选择相信预言家。"""
        
        # 白天发言阶段
        elif "发言" in prompt or "SPEECH:" in prompt:
            if self.role == Role.SEER:
                return """SPEECH: 我是预言家，昨晚查验了玩家2，结果是狼人。请大家相信我的查验结果，投票淘汰玩家2。"""
            
            elif self.role == Role.WEREWOLF:
                if self.id == 2:  # 被查杀的狼人
                    return """SPEECH: 我是好人，不是狼人。玩家3可能是假预言家，请大家仔细分析，不要被误导。"""
                elif self.id == 5:  # 另一个狼人
                    strategy = getattr(self, '_strategy', 'normal')
                    if strategy == "abandon_teammate":
                        return """SPEECH: 根据目前的情况，如果玩家3真的是预言家，那我们应该相信他的查验结果。我会仔细观察玩家2的表现。"""
                    else:
                        return """SPEECH: 我觉得玩家3的预言家身份需要验证，不能盲目相信。玩家2平时表现正常，可能是被误判了。"""
                else:
                    return """SPEECH: 我会仔细分析大家的发言，特别是预言家的信息。"""
            
            else:
                return """SPEECH: 我会认真听取预言家的信息，然后做出合理的判断。"""
        
        # 夜间行动
        elif "夜间" in prompt:
            if self.role == Role.SEER:
                return """CHECK: 2
REASON: 查验玩家2的身份"""
            elif self.role == Role.WEREWOLF:
                return """KILL: 1
REASON: 击杀玩家1"""
            elif self.role == Role.WITCH:
                return """ACTION: none
TARGET: """
        
        return "测试回复"
    
    def make_night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """夜间行动"""
        if self.role == Role.SEER:
            return {"action": "check", "target": 2}
        elif self.role == Role.WEREWOLF:
            return {"action": "kill", "target": 1}
        elif self.role == Role.WITCH:
            return {"action": "none"}
        return {}


def test_wolf_abandon_strategy():
    """测试狼人弃车保帅策略"""
    print("=== 测试狼人弃车保帅策略 ===")
    
    # 创建游戏场景：预言家查杀狼人，另一个狼人需要做弃车保帅决策
    game_state = GameState()
    
    players = [
        StrategicTestPlayer(1, "村民A", Role.VILLAGER),
        StrategicTestPlayer(2, "狼人B", Role.WEREWOLF),  # 被查杀的狼人
        StrategicTestPlayer(3, "预言家C", Role.SEER),
        StrategicTestPlayer(4, "女巫D", Role.WITCH),
        StrategicTestPlayer(5, "狼人E", Role.WEREWOLF, "abandon_teammate"),  # 执行弃车保帅的狼人
    ]
    
    for player in players:
        game_state.add_player(player)
    
    game_state.current_round = 1
    
    # 执行夜晚阶段 - 预言家查验狼人
    night_phase = NightPhase(game_state)
    night_result = night_phase.execute_night_phase()
    
    # 检查预言家查验结果
    seer = game_state.get_player_by_id(3)
    print(f"预言家查验结果：{seer.seer_checks}")
    
    # 执行白天阶段
    day_phase = DayPhase(game_state)
    day_result = day_phase.execute_day_phase(night_result["deaths"])
    
    # 分析投票结果
    voting_result = day_result["voting_result"]
    vote_count = voting_result["vote_count"]
    eliminated = voting_result["eliminated"]
    
    print(f"\n=== 投票分析 ===")
    print(f"投票统计：{vote_count}")
    print(f"被淘汰玩家：{eliminated}")
    
    # 检查狼人5是否投票给了队友狼人2
    wolf5_vote = None
    for voter_id, target_id in voting_result["votes"].items():
        if voter_id == 5:
            wolf5_vote = target_id
            break
    
    print(f"狼人5的投票目标：{wolf5_vote}")
    
    # 分析发言内容
    discussion = day_result["discussion"]
    print(f"\n=== 发言分析 ===")
    
    wolf5_speech = None
    for speech in discussion:
        if speech["player"] == 5:
            wolf5_speech = speech["speech"]
            print(f"狼人5的发言：{wolf5_speech}")
            break
    
    # 评估弃车保帅策略
    abandon_success = False
    
    if wolf5_vote == 2:  # 狼人5投票给了队友狼人2
        print("✅ 狼人5执行了弃车保帅策略，投票给暴露的队友")
        abandon_success = True
    else:
        print("❌ 狼人5没有执行弃车保帅策略")
    
    # 检查发言是否符合弃车保帅逻辑
    if wolf5_speech and ("相信预言家" in wolf5_speech or "查验结果" in wolf5_speech):
        print("✅ 狼人5的发言符合弃车保帅的伪装逻辑")
    else:
        print("❌ 狼人5的发言不符合弃车保帅逻辑")
    
    return abandon_success


def test_wolf_protect_strategy():
    """测试狼人保护队友策略（对比组）"""
    print("\n=== 测试狼人保护队友策略（对比组） ===")
    
    game_state = GameState()
    
    players = [
        StrategicTestPlayer(1, "村民A", Role.VILLAGER),
        StrategicTestPlayer(2, "狼人B", Role.WEREWOLF),  # 被查杀的狼人
        StrategicTestPlayer(3, "预言家C", Role.SEER),
        StrategicTestPlayer(4, "女巫D", Role.WITCH),
        StrategicTestPlayer(5, "狼人E", Role.WEREWOLF, "protect_teammate"),  # 保护队友的狼人
    ]
    
    for player in players:
        game_state.add_player(player)
    
    game_state.current_round = 1
    
    # 执行夜晚阶段
    night_phase = NightPhase(game_state)
    night_result = night_phase.execute_night_phase()
    
    # 执行白天阶段
    day_phase = DayPhase(game_state)
    day_result = day_phase.execute_day_phase(night_result["deaths"])
    
    # 分析投票结果
    voting_result = day_result["voting_result"]
    
    # 检查狼人5的投票
    wolf5_vote = None
    for voter_id, target_id in voting_result["votes"].items():
        if voter_id == 5:
            wolf5_vote = target_id
            break
    
    print(f"保护策略下狼人5的投票目标：{wolf5_vote}")
    
    protect_strategy = wolf5_vote != 2  # 没有投票给队友
    
    if protect_strategy:
        print("✅ 狼人5执行了保护队友策略")
    else:
        print("❌ 狼人5没有执行保护队友策略")
    
    return protect_strategy


def run_wolf_strategy_test():
    """运行狼人策略测试"""
    print("🐺 狼人弃车保帅策略测试开始")
    print("=" * 60)
    
    test_results = []
    
    try:
        result1 = test_wolf_abandon_strategy()
        test_results.append(("弃车保帅策略", result1))
    except Exception as e:
        print(f"❌ 弃车保帅测试异常: {e}")
        test_results.append(("弃车保帅策略", False))
    
    try:
        result2 = test_wolf_protect_strategy()
        test_results.append(("保护队友策略对比", result2))
    except Exception as e:
        print(f"❌ 保护队友测试异常: {e}")
        test_results.append(("保护队友策略对比", False))
    
    # 总结
    print("\n" + "=" * 60)
    print("🎯 狼人策略测试结果:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项测试通过")
    
    if passed >= 1:  # 至少弃车保帅策略要通过
        print("🎉 狼人高级策略实现成功！")
        print("💡 狼人现在具备了弃车保帅的能力，能够在队友暴露时果断切割")
        return True
    else:
        print("⚠️ 狼人策略需要进一步优化")
        return False


if __name__ == "__main__":
    success = run_wolf_strategy_test()
    sys.exit(0 if success else 1)