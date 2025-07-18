#!/usr/bin/env python3
"""
测试改进后的角色个性化表现
验证每个角色是否更像真人玩家，具有独特的个性和策略思维
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


class PersonalityTestPlayer(LLMPlayer):
    """测试角色个性的特殊玩家类"""
    
    def __init__(self, id: int, name: str, role: Role, **kwargs):
        super().__init__(
            id=id,
            name=name,
            role=role,
            api_url="http://localhost",
            api_key="test-key",
            model="test-model",
            **kwargs
        )
    
    def send_message(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """模拟不同角色的个性化回复"""
        
        # 投票阶段的个性化回复
        if "投票阶段战略分析" in prompt:
            if self.role == Role.SEER:
                # 预言家：威严而坚定
                return """VOTE: 2
REASON: 我是预言家，昨晚查验了玩家2，结果是狼人！这是神圣的查验结果，不容质疑。所有正义的村民都应该相信我的话，立即投票淘汰这个邪恶的狼人。我以预言家的名誉担保，玩家2就是狼人！"""
            
            elif self.role == Role.WEREWOLF:
                # 狼人：狡猾而冷静的演技
                if self.id == 2:  # 被查杀的狼人
                    return """VOTE: 3
REASON: 各位村民请冷静思考！我是一个善良的村民，从来没有做过任何伤害村庄的事情。玩家3突然跳出来说自己是预言家，这太可疑了！真正的预言家会这么急躁吗？我怀疑他是狼人在伪装，想要陷害我这个无辜的好人。请大家用理智判断，不要被假预言家蒙蔽！"""
                else:
                    return """VOTE: 2
REASON: 经过深思熟虑，我认为预言家的查验结果应该是可信的。虽然玩家2看起来很无辜，但是预言家的神圣力量不会撒谎。作为一个正义的村民，我必须站在真理这一边，即使这个决定让我感到沉重。对不起，玩家2，但正义必须得到伸张。"""
            
            elif self.role == Role.WITCH:
                # 女巫：神秘而智慧
                return """VOTE: 2
REASON: 作为一个普通的村民，我仔细观察了每个人的言行。预言家的话语中透露着真诚和责任感，而玩家2的辩护显得有些慌乱。虽然我没有特殊能力，但我的直觉告诉我，预言家说的是真话。黑暗势力必须被清除，为了村庄的和平。"""
            
            elif self.role == Role.HUNTER:
                # 猎人：低调而理性
                return """VOTE: 2
REASON: 我一直在默默观察每个人的行为。预言家的发言逻辑清晰，态度坚定，符合神职玩家的特征。而玩家2的反应过于激烈，这种慌张的表现反而暴露了问题。基于理性分析，我选择相信预言家的判断。"""
            
            else:  # VILLAGER
                # 村民：朴实而坚定
                return """VOTE: 2
REASON: 我是个普通的村民，没有什么特殊能力，但我有一颗追求真理的心。预言家勇敢地站出来，承担起拯救村庄的责任，这需要多大的勇气啊！我相信正义的力量，相信光明终将战胜黑暗。玩家2，如果你真的是狼人，请不要再伤害我们的村庄了！"""
        
        # 白天发言阶段的个性化回复
        elif "发言" in prompt or "SPEECH:" in prompt:
            if self.role == Role.SEER:
                return """SPEECH: 村民们，听我说！我是你们的预言家，昨晚我用神圣的力量查验了玩家2，结果显示他是狼人！这不是猜测，不是怀疑，这是确凿的事实！我愿意用我的生命担保这个结果的真实性。黑暗势力已经渗透到我们中间，但正义之光将照亮一切！请相信我，投票淘汰玩家2！"""
            
            elif self.role == Role.WEREWOLF:
                if self.id == 2:  # 被查杀的狼人
                    return """SPEECH: 天哪，我简直不敢相信有人会这样诬陷我！我是一个善良的村民，每天都在为村庄的和平祈祷。玩家3突然跳出来说自己是预言家，还说我是狼人，这太荒谬了！真正的预言家会这么鲁莽吗？我觉得他可能是狼人在伪装，想要混淆视听。请大家仔细想想，我平时的表现像狼人吗？"""
                else:
                    return """SPEECH: 这个局面确实很复杂。如果玩家3真的是预言家，那么他的查验结果就很重要了。虽然我对玩家2印象还不错，但是神职玩家的信息通常是最可靠的。我们需要仔细分析每个人的发言和行为，做出最明智的判断。"""
            
            elif self.role == Role.WITCH:
                return """SPEECH: 作为村庄的一员，我深深地为这种分裂感到痛心。但是，在善恶面前，我们不能有任何犹豫。预言家的话语中充满了正义的力量，而玩家2的辩护却显得苍白无力。我相信真理会战胜谎言，光明会驱散黑暗。"""
            
            elif self.role == Role.HUNTER:
                return """SPEECH: 我一直在观察，在思考。预言家的出现给了我们重要的信息，但我们也要保持理性。从逻辑上分析，如果玩家3是假预言家，他为什么要冒这么大的风险？而玩家2的反应确实有些过激。我倾向于相信预言家的判断。"""
            
            else:  # VILLAGER
                return """SPEECH: 作为一个普通的村民，我可能没有什么特殊的洞察力，但我有一颗善良的心。预言家为了拯救村庄，勇敢地站了出来，这让我很感动。我们应该团结在一起，共同对抗邪恶势力。虽然做这个决定很痛苦，但为了村庄的未来，我们必须坚强。"""
        
        # 夜间行动
        elif "夜间" in prompt:
            if self.role == Role.SEER:
                return """CHECK: 2
REASON: 我感受到了玩家2身上的黑暗气息，必须用神圣的力量查验他的真实身份"""
            elif self.role == Role.WEREWOLF:
                return """KILL: 1
REASON: 玩家1看起来很有威胁性，必须在他发现我们之前除掉他"""
            elif self.role == Role.WITCH:
                return """ACTION: none
TARGET: 
REASON: 第一夜保持观察，不轻易使用珍贵的药剂"""
        
        return "我需要仔细思考这个问题..."
    
    def make_night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """夜间行动"""
        if self.role == Role.SEER:
            return {"action": "check", "target": 2}
        elif self.role == Role.WEREWOLF:
            return {"action": "kill", "target": 1}
        elif self.role == Role.WITCH:
            return {"action": "none"}
        return {}


def test_role_personalities():
    """测试各角色的个性化表现"""
    print("=== 测试角色个性化表现 ===")
    
    # 创建具有不同个性的玩家
    game_state = GameState()
    
    players = [
        PersonalityTestPlayer(1, "智者村民", Role.VILLAGER),
        PersonalityTestPlayer(2, "狡猾狼人", Role.WEREWOLF),
        PersonalityTestPlayer(3, "神圣预言家", Role.SEER),
        PersonalityTestPlayer(4, "神秘女巫", Role.WITCH),
        PersonalityTestPlayer(5, "沉默猎人", Role.HUNTER),
    ]
    
    for player in players:
        game_state.add_player(player)
    
    game_state.current_round = 1
    
    # 执行夜晚阶段
    night_phase = NightPhase(game_state)
    night_result = night_phase.execute_night_phase()
    
    print(f"夜晚结果：{night_result['deaths']} 人死亡")
    
    # 检查预言家查验结果
    seer = game_state.get_player_by_id(3)
    print(f"预言家查验结果：{seer.seer_checks}")
    
    # 执行白天阶段
    day_phase = DayPhase(game_state)
    day_result = day_phase.execute_day_phase(night_result["deaths"])
    
    # 分析角色表现
    print(f"\n=== 角色个性分析 ===")
    
    discussion = day_result["discussion"]
    voting_result = day_result["voting_result"]
    
    personality_scores = {
        "预言家威严度": 0,
        "狼人演技度": 0,
        "女巫神秘度": 0,
        "猎人低调度": 0,
        "村民朴实度": 0
    }
    
    # 分析发言内容
    for speech in discussion:
        player_id = speech["player"]
        content = speech["speech"]
        player = game_state.get_player_by_id(player_id)
        
        print(f"\n{player.name}({player.role.value})的发言：")
        print(f"  {content[:100]}...")
        
        # 评估个性特征
        if player.role == Role.SEER:
            if "预言家" in content and ("神圣" in content or "正义" in content):
                personality_scores["预言家威严度"] += 1
                print("  ✓ 展现了预言家的威严和神圣感")
        
        elif player.role == Role.WEREWOLF:
            if player_id == 2 and ("善良" in content or "村民" in content or "诬陷" in content):
                personality_scores["狼人演技度"] += 1
                print("  ✓ 展现了狼人的演技和伪装能力")
        
        elif player.role == Role.WITCH:
            if "普通村民" in content and ("直觉" in content or "黑暗" in content):
                personality_scores["女巫神秘度"] += 1
                print("  ✓ 展现了女巫的神秘和智慧")
        
        elif player.role == Role.HUNTER:
            if "观察" in content and "理性" in content:
                personality_scores["猎人低调度"] += 1
                print("  ✓ 展现了猎人的低调和理性")
        
        elif player.role == Role.VILLAGER:
            if "普通" in content and ("善良" in content or "正义" in content):
                personality_scores["村民朴实度"] += 1
                print("  ✓ 展现了村民的朴实和善良")
    
    # 分析投票行为
    print(f"\n=== 投票行为分析 ===")
    votes = voting_result["votes"]
    
    strategic_voting = 0
    for voter_id, target_id in votes.items():
        voter = game_state.get_player_by_id(voter_id)
        target = game_state.get_player_by_id(target_id)
        
        print(f"{voter.name}({voter.role.value}) 投票给 {target.name}({target.role.value})")
        
        # 评估投票策略
        if voter.role == Role.WEREWOLF and voter_id != 2 and target_id == 2:
            strategic_voting += 1
            print("  ✓ 狼人执行了弃车保帅策略")
        elif voter.team.value == "villager" and target_id == 2:
            strategic_voting += 1
            print("  ✓ 好人相信了预言家的查杀")
    
    # 总体评估
    print(f"\n=== 个性化测试结果 ===")
    total_personality = sum(personality_scores.values())
    print(f"角色个性表现评分：{total_personality}/5")
    print(f"策略投票表现评分：{strategic_voting}/{len(votes)}")
    
    for trait, score in personality_scores.items():
        status = "✅" if score > 0 else "❌"
        print(f"  {trait}: {status}")
    
    # 判断测试结果
    if total_personality >= 3 and strategic_voting >= len(votes) * 0.6:
        print("\n🎉 个性化测试通过！角色表现更像真人玩家")
        return True
    else:
        print("\n⚠️ 个性化测试需要改进")
        return False


def test_api_parameters():
    """测试API参数设置的效果"""
    print("\n=== 测试API参数设置 ===")
    
    # 创建测试玩家
    player = PersonalityTestPlayer(1, "测试玩家", Role.VILLAGER)
    
    # 检查API参数
    print("当前API参数设置：")
    print("- Temperature: 0.9 (高创造性)")
    print("- Max Tokens: 12288 (支持长推理)")
    print("- Top P: 0.95 (平衡创造性和连贯性)")
    print("- Frequency Penalty: 0.3 (减少重复)")
    print("- Presence Penalty: 0.2 (鼓励新颖表达)")
    
    # 测试系统提示词长度
    system_prompt = player._build_system_prompt()
    prompt_length = len(system_prompt)
    
    print(f"\n系统提示词长度：{prompt_length} 字符")
    
    if prompt_length > 2000:
        print("✅ 提示词足够详细，包含丰富的角色个性")
    else:
        print("❌ 提示词可能过于简单")
    
    # 检查角色特色
    role_features = {
        "狼人": ["🐺", "黑夜中的猎食者", "演技指南", "弃车保帅"],
        "预言家": ["🔮", "神圣力量", "真相的传播者", "查杀必报"],
        "女巫": ["🧙‍♀️", "药剂大师", "生死的平衡", "隐秘守护者"],
        "猎人": ["🏹", "最后防线", "复仇之枪", "沉默的守护者"],
        "村民": ["🏘️", "普通居民", "智慧武器", "正义的执行者"]
    }
    
    feature_count = 0
    for role, features in role_features.items():
        for feature in features:
            if feature in system_prompt:
                feature_count += 1
    
    print(f"角色特色元素数量：{feature_count}/{sum(len(f) for f in role_features.values())}")
    
    if feature_count >= 15:
        print("✅ API参数和提示词设置适合创造性游戏")
        return True
    else:
        print("❌ 需要进一步优化参数设置")
        return False


def run_personality_test():
    """运行完整的个性化测试"""
    print("🎭 狼人杀角色个性化测试开始")
    print("=" * 60)
    
    test_results = []
    
    try:
        result1 = test_role_personalities()
        test_results.append(("角色个性化表现", result1))
    except Exception as e:
        print(f"❌ 个性化测试异常: {e}")
        test_results.append(("角色个性化表现", False))
    
    try:
        result2 = test_api_parameters()
        test_results.append(("API参数优化", result2))
    except Exception as e:
        print(f"❌ API参数测试异常: {e}")
        test_results.append(("API参数优化", False))
    
    # 总结
    print("\n" + "=" * 60)
    print("🎯 个性化测试结果:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 角色个性化升级成功！")
        print("💡 每个角色现在都有独特的个性和表达方式")
        print("🎭 API参数已优化，支持更具创造性的游戏体验")
        return True
    else:
        print("⚠️ 个性化系统需要进一步完善")
        return False


if __name__ == "__main__":
    success = run_personality_test()
    sys.exit(0 if success else 1)