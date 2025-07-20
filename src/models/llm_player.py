import json
import requests
import re
from typing import Dict, List, Optional, Any
from pydantic import Field
from .player import Player, Role, PlayerStatus
from ..utils.hallucination_detector import MultiLayerHallucinationDetector
from ..utils.speech_corrector import IntelligentSpeechCorrector
from ..utils.context_builder import EnhancedContextBuilder
from .hallucination_models import HallucinationReductionConfig


# 身份约束规则系统
IDENTITY_CONSTRAINTS = {
    Role.VILLAGER: {
        "can_claim": [Role.VILLAGER],
        "cannot_claim": [Role.SEER, Role.WITCH, Role.HUNTER, Role.WEREWOLF],
        "can_fake_claim": [],  # 村民不建议假跳
        "strategy_notes": "专注于逻辑分析，不要声称拥有特殊能力"
    },
    Role.WEREWOLF: {
        "can_claim": [Role.VILLAGER],
        "cannot_claim": [],  # 狼人可以伪装任何身份
        "can_fake_claim": [Role.SEER, Role.WITCH, Role.HUNTER],
        "strategy_notes": "可以伪装身份，但需要有合理的策略理由"
    },
    Role.SEER: {
        "can_claim": [Role.SEER, Role.VILLAGER],
        "cannot_claim": [Role.WITCH, Role.HUNTER, Role.WEREWOLF],
        "can_fake_claim": [],
        "strategy_notes": "可以选择隐藏或公开身份，但查验结果必须真实"
    },
    Role.WITCH: {
        "can_claim": [Role.WITCH, Role.VILLAGER],
        "cannot_claim": [Role.SEER, Role.HUNTER, Role.WEREWOLF],
        "can_fake_claim": [],
        "strategy_notes": "建议隐藏身份，白天表现得像普通村民"
    },
    Role.HUNTER: {
        "can_claim": [Role.HUNTER, Role.VILLAGER],
        "cannot_claim": [Role.SEER, Role.WITCH, Role.WEREWOLF],
        "can_fake_claim": [],
        "strategy_notes": "建议隐藏身份，威慑作用比公开更重要"
    }
}

# 第一轮游戏约束规则
FIRST_ROUND_CONSTRAINTS = {
    "available_information": [
        "玩家列表和编号",
        "夜晚死亡公告",
        "死亡玩家遗言（如果有）"
    ],
    "unavailable_information": [
        "前夜查验结果",
        "玩家互动历史",
        "复杂的行为分析",
        "投票历史"
    ],
    "recommended_focus": [
        "基础游戏规则",
        "遗言信息分析",
        "简单逻辑推理",
        "身份合理性判断"
    ],
    "forbidden_references": [
        "前夜", "昨天的查验", "之前的互动", "历史行为",
        "前面轮次", "上一轮", "之前发生", "历史记录"
    ]
}

# 发言模板系统
SPEECH_TEMPLATES = {
    "first_round_villager": {
        "opening": "我是{name}，编号{id}。这是第一轮，信息有限。",
        "analysis_focus": "基于遗言信息和基础逻辑",
        "conclusion": "建议大家谨慎分析，避免盲目投票。",
        "forbidden_elements": ["前夜查验", "复杂互动分析", "虚假身份声明"]
    },
    "first_round_seer": {
        "opening": "我是{name}，编号{id}。",
        "identity_options": ["隐藏身份", "暗示查验结果", "直接公开"],
        "result_sharing": "如果选择分享：昨晚我查验了{target}，结果是{result}",
        "forbidden_elements": ["虚假查验结果", "编造互动历史"]
    },
    "first_round_werewolf": {
        "opening": "我是{name}，编号{id}。",
        "disguise_options": ["表现为村民", "假跳神职", "质疑他人"],
        "strategy_focus": "混淆视听，保护队友",
        "forbidden_elements": ["暴露狼人身份", "为队友过度辩护"]
    },
    "first_round_witch": {
        "opening": "我是{name}，编号{id}。",
        "disguise_strategy": "完全表现为普通村民",
        "analysis_approach": "基于遗言和基础逻辑",
        "forbidden_elements": ["暴露女巫身份", "提及药剂使用"]
    },
    "first_round_hunter": {
        "opening": "我是{name}，编号{id}。",
        "disguise_strategy": "低调表现，不引人注目",
        "analysis_approach": "理性分析，避免成为焦点",
        "forbidden_elements": ["暴露猎人身份", "威胁开枪"]
    }
}


class RealityConstraintValidator:
    """现实约束验证器，检测和修正LLM发言中的幻觉内容"""
    
    def __init__(self, game_state=None):
        self.game_state = game_state
    
    def validate_speech_content(self, player_id: int, player_role: Role, speech: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """验证发言内容的现实性"""
        issues = []
        
        # 检查身份声明
        identity_issues = self._detect_identity_hallucination(speech, player_role)
        issues.extend(identity_issues)
        
        # 检查时间线引用
        if context and context.get("round", 1) == 1:
            temporal_issues = self._detect_temporal_hallucination(speech, 1)
            issues.extend(temporal_issues)
        
        # 检查事件引用
        event_issues = self._detect_event_hallucination(speech, context)
        issues.extend(event_issues)
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "corrected_speech": self._generate_corrected_speech(speech, issues, player_role, context) if issues else speech
        }
    
    def _detect_identity_hallucination(self, speech: str, player_role: Role) -> List[str]:
        """检测身份相关的幻觉，使用身份约束规则"""
        issues = []
        
        # 获取该角色的约束规则
        constraints = IDENTITY_CONSTRAINTS.get(player_role, {})
        cannot_claim = constraints.get("cannot_claim", [])
        can_fake_claim = constraints.get("can_fake_claim", [])
        
        # 检测各种身份声明
        identity_claims = {
            "预言家": Role.SEER,
            "女巫": Role.WITCH,
            "猎人": Role.HUNTER,
            "狼人": Role.WEREWOLF,
            "村民": Role.VILLAGER
        }
        
        for claim_text, claim_role in identity_claims.items():
            if f"我是{claim_text}" in speech or f"作为{claim_text}" in speech:
                if claim_role in cannot_claim:
                    # 检查是否是允许的假跳
                    if claim_role in can_fake_claim and self._has_strategic_reason_for_fake_claim(speech):
                        continue  # 允许策略性假跳
                    else:
                        issues.append(f"{player_role.value}不应声称是{claim_text}")
        
        # 检测虚假查验结果
        if ("我查验了" in speech or "查验结果" in speech) and player_role != Role.SEER:
            issues.append("只有预言家才能有查验结果")
        
        return issues
    
    def _detect_temporal_hallucination(self, speech: str, round_num: int) -> List[str]:
        """检测时间线相关的幻觉"""
        issues = []
        
        if round_num == 1:
            temporal_keywords = [
                "前夜", "昨天的查验", "之前的互动", "历史行为", 
                "前面轮次", "上一轮", "之前发生", "历史记录"
            ]
            for keyword in temporal_keywords:
                if keyword in speech:
                    issues.append(f"第一轮不应引用: {keyword}")
        
        return issues
    
    def _detect_event_hallucination(self, speech: str, context: Dict[str, Any] = None) -> List[str]:
        """检测事件引用相关的幻觉"""
        issues = []
        
        # 检测编造的玩家互动
        interaction_patterns = [
            r"(\w+)对我说", r"我和(\w+)讨论", r"(\w+)告诉我", 
            r"(\w+)私下", r"(\w+)暗示我"
        ]
        
        for pattern in interaction_patterns:
            if re.search(pattern, speech):
                issues.append("不应编造玩家间的私下互动")
                break
        
        return issues
    
    def _has_strategic_reason_for_fake_claim(self, speech: str) -> bool:
        """检查狼人假跳是否有合理的策略理由"""
        strategic_keywords = [
            "为了", "策略", "混淆", "误导", "保护队友", 
            "反击", "对抗", "查杀", "压力"
        ]
        return any(keyword in speech for keyword in strategic_keywords)
    
    def _generate_corrected_speech(self, speech: str, issues: List[str], player_role: Role, context: Dict[str, Any] = None) -> str:
        """生成修正后的发言"""
        corrected = speech
        
        # 修正身份声明错误
        if player_role == Role.VILLAGER:
            corrected = re.sub(r'我是(预言家|女巫|猎人)', '我是村民', corrected)
            corrected = re.sub(r'作为(预言家|女巫|猎人)', '作为村民', corrected)
            corrected = re.sub(r'我查验了.*?结果', '根据分析', corrected)
        
        # 修正时间线错误
        if context and context.get("round", 1) == 1:
            corrections = {
                "前夜": "昨晚",
                "之前的查验": "可能的查验",
                "历史行为": "当前行为",
                "前面轮次": "这一轮",
                "上一轮": "这一轮"
            }
            for wrong, right in corrections.items():
                corrected = corrected.replace(wrong, right)
        
        # 移除编造的互动
        corrected = re.sub(r'\w+对我说.*?[。！]', '', corrected)
        corrected = re.sub(r'我和\w+讨论.*?[。！]', '', corrected)
        
        return corrected.strip()


class HallucinationDetector:
    """专门的幻觉检测器，检测各类幻觉内容"""
    
    def __init__(self):
        pass
    
    def detect_identity_hallucination(self, speech: str, player_role: Role) -> List[str]:
        """检测身份相关的幻觉"""
        issues = []
        
        # 使用身份约束规则
        constraints = IDENTITY_CONSTRAINTS.get(player_role, {})
        cannot_claim = constraints.get("cannot_claim", [])
        can_fake_claim = constraints.get("can_fake_claim", [])
        
        # 检测各种身份声明
        identity_claims = {
            "预言家": Role.SEER,
            "女巫": Role.WITCH,
            "猎人": Role.HUNTER,
            "狼人": Role.WEREWOLF,
            "村民": Role.VILLAGER
        }
        
        for claim_text, claim_role in identity_claims.items():
            if f"我是{claim_text}" in speech or f"作为{claim_text}" in speech:
                if claim_role in cannot_claim:
                    # 检查是否是允许的假跳
                    if claim_role in can_fake_claim and self._has_strategic_reason(speech):
                        continue  # 允许策略性假跳
                    else:
                        issues.append(f"{player_role.value}不应声称是{claim_text}")
        
        return issues
    
    def detect_temporal_hallucination(self, speech: str, round_num: int) -> List[str]:
        """检测时间线相关的幻觉"""
        issues = []
        
        if round_num == 1:
            # 使用第一轮约束规则
            forbidden_refs = FIRST_ROUND_CONSTRAINTS.get("forbidden_references", [])
            for keyword in forbidden_refs:
                if keyword in speech:
                    issues.append(f"第一轮不应引用: {keyword}")
        
        return issues
    
    def detect_event_hallucination(self, speech: str, context: Dict[str, Any] = None) -> List[str]:
        """检测事件引用相关的幻觉"""
        issues = []
        
        # 检测编造的玩家互动
        interaction_patterns = [
            r"(\w+)对我说", r"我和(\w+)讨论", r"(\w+)告诉我", 
            r"(\w+)私下", r"(\w+)暗示我"
        ]
        
        for pattern in interaction_patterns:
            if re.search(pattern, speech):
                issues.append("不应编造玩家间的私下互动")
                break
        
        return issues
    
    def _has_strategic_reason(self, speech: str) -> bool:
        """检查是否有合理的策略理由"""
        strategic_keywords = [
            "为了", "策略", "混淆", "误导", "保护队友", 
            "反击", "对抗", "查杀", "压力"
        ]
        return any(keyword in speech for keyword in strategic_keywords)


class SpeechCorrector:
    """发言修正器，自动修正幻觉内容"""
    
    def __init__(self):
        pass
    
    def correct_identity_claims(self, speech: str, player_role: Role) -> str:
        """修正身份声明错误"""
        corrected = speech
        
        if player_role == Role.VILLAGER:
            # 移除虚假神职声明
            corrected = re.sub(r'我是(预言家|女巫|猎人)', '我是村民', corrected)
            corrected = re.sub(r'作为(预言家|女巫|猎人)', '作为村民', corrected)
            corrected = re.sub(r'我查验了.*?结果', '根据分析', corrected)
        
        return corrected
    
    def correct_temporal_references(self, speech: str, round_num: int) -> str:
        """修正时间线错误"""
        corrected = speech
        
        if round_num == 1:
            # 替换不当的时间引用
            corrections = {
                "前夜": "昨晚",
                "之前的查验": "可能的查验",
                "历史行为": "当前行为",
                "前面轮次": "这一轮",
                "上一轮": "这一轮"
            }
            for wrong, right in corrections.items():
                corrected = corrected.replace(wrong, right)
        
        return corrected
    
    def correct_event_references(self, speech: str) -> str:
        """修正事件引用错误"""
        corrected = speech
        
        # 移除编造的互动
        corrected = re.sub(r'\w+对我说.*?[。！]', '', corrected)
        corrected = re.sub(r'我和\w+讨论.*?[。！]', '', corrected)
        
        return corrected.strip()
    
    def apply_comprehensive_correction(self, speech: str, issues: List[str], player_role: Role, context: Dict[str, Any] = None) -> str:
        """应用综合修正"""
        corrected = speech
        
        # 修正身份声明
        corrected = self.correct_identity_claims(corrected, player_role)
        
        # 修正时间线引用
        if context and context.get("round", 1) == 1:
            corrected = self.correct_temporal_references(corrected, 1)
        
        # 修正事件引用
        corrected = self.correct_event_references(corrected)
        
        return corrected


class LLMPlayer(Player):
    conversation_history: List[Dict[str, str]] = []
    speech_quality_log: List[Dict[str, Any]] = []
    hallucination_detection_log: List[Dict[str, Any]] = []
    correction_history: List[Dict[str, Any]] = []
    hallucination_config: Optional[HallucinationReductionConfig] = Field(default=None)
    hallucination_detector: Optional[Any] = Field(default=None)
    speech_corrector: Optional[Any] = Field(default=None)
    context_builder: Optional[Any] = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # Initialize enhanced hallucination reduction components
        if self.hallucination_config is None:
            self.hallucination_config = HallucinationReductionConfig()
        if self.hallucination_detector is None:
            self.hallucination_detector = MultiLayerHallucinationDetector(self.hallucination_config)
        if self.speech_corrector is None:
            self.speech_corrector = IntelligentSpeechCorrector(self.hallucination_config)
        if self.context_builder is None:
            self.context_builder = EnhancedContextBuilder(self.hallucination_config)
        
    def send_message(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Send a message to the LLM and get response"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Prepare the full context for the LLM
            system_prompt = self._build_system_prompt()
            full_prompt = self._build_full_prompt(prompt, context)
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": 0.9,  # 提高温度以增加创造性和多样性
                "max_tokens": 12288,  # 增加token限制以支持更长的推理
                "top_p": 0.95,  # 添加top_p参数以平衡创造性和连贯性
                "frequency_penalty": 0.3,  # 减少重复表达
                "presence_penalty": 0.2   # 鼓励新颖的表达方式
            }
            
            response = requests.post(
                f"{self.api_url}",
                headers=headers,
                json=payload,
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result["choices"][0]["message"]["content"]
                
                # Log the conversation
                self.conversation_history.append({
                    "prompt": prompt,
                    "context": context,
                    "response": llm_response,
                    "timestamp": "current"
                })
                
                return llm_response
            else:
                return f"Error: API returned status {response.status_code}"
                
        except Exception as e:
            return f"Error communicating with LLM: {str(e)}"
    
    def _build_system_prompt(self) -> str:
        """构建简洁明确的系统提示词，避免复杂角色扮演"""
        # 基础身份信息（简洁版）
        base_info = f"""你是狼人杀游戏中的玩家{self.name}（编号{self.id}）。

身份信息：
- 真实身份：{self.get_role_description()}
- 所属阵营：{self.team.value if hasattr(self.team, 'value') else self.team}
- 生存状态：{"存活" if self.is_alive() else "死亡"}

游戏目标：
{self._get_simple_objective()}

重要约束：
1. 只能基于真实发生的游戏事件进行推理和发言
2. 不能编造不存在的玩家互动、发言内容或游戏事件
3. 身份声明必须符合游戏规则和你的真实身份
4. 第一轮游戏时没有前夜信息，不能引用不存在的历史互动
5. 发言要实事求是，基于当前已知的确切信息

"""
        
        # 角色特定指令（简化版）
        role_instructions = self._get_role_specific_instructions()
        
        return base_info + role_instructions
    
    def _get_simple_objective(self) -> str:
        """获取简化的游戏目标描述"""
        if self.team.value == "werewolf":
            return "消灭所有好人，让狼人数量大于等于好人数量"
        else:
            return "找出并投票淘汰所有狼人"
    
    def _get_role_specific_instructions(self) -> str:
        """获取角色特定的简化指令"""
        if self.role == Role.VILLAGER:
            return """角色能力：无特殊能力
行为规则：
1. 通过逻辑推理找出狼人
2. 相信预言家的查验结果
3. 不要声称拥有特殊能力
4. 基于事实进行发言和投票

发言约束：
- 不能声称自己是预言家、女巫或猎人
- 不能编造查验结果或特殊信息
- 应该支持真正的神职玩家"""

        elif self.role == Role.SEER:
            return f"""角色能力：每晚可以查验一名玩家的身份
当前查验记录：{self.seer_checks}

行为规则：
1. 每晚必须选择一名玩家进行查验
2. 可以选择公开或隐藏身份
3. 查验结果必须真实，不能编造
4. 死亡时应在遗言中公开所有查验结果

身份公开策略：
- 查到狼人时建议公开身份并报告查杀
- 可以选择适当时机跳出来指导好人
- 面对质疑时要坚持查验结果的真实性"""

        elif self.role == Role.WITCH:
            heal_status = "可用" if self.witch_potions.get("heal", False) else "已使用"
            poison_status = "可用" if self.witch_potions.get("poison", False) else "已使用"
            
            return f"""角色能力：拥有解药和毒药各一瓶
当前药剂状态：
- 解药：{heal_status}
- 毒药：{poison_status}

行为规则：
1. 夜晚可以选择使用解药救人或毒药杀人
2. 绝对不能暴露女巫身份
3. 白天发言要像普通村民一样
4. 重视预言家的查验结果作为用药参考

用药策略：
- 解药优先救重要的好人（如预言家）
- 毒药只在确定目标是狼人时使用
- 保持身份隐秘是生存的关键"""

        elif self.role == Role.HUNTER:
            shoot_status = "可用" if self.hunter_can_shoot else "已失效"
            
            return f"""角色能力：死亡时可以开枪带走一名玩家
当前状态：开枪能力{shoot_status}

行为规则：
1. 平时要保持低调，不暴露猎人身份
2. 死亡时可以选择开枪带走一名玩家
3. 白天发言要像普通村民一样
4. 开枪目标应该选择最可疑的狼人

生存策略：
- 隐藏身份，避免成为狼人优先目标
- 观察分析，为可能的开枪做准备
- 威慑作用有时比实际开枪更重要"""

        elif self.role == Role.WEREWOLF:
            return """角色能力：夜晚与狼队友商议击杀目标
阵营目标：消灭好人，隐藏身份

行为规则：
1. 白天必须伪装成好人
2. 可以适当时候假跳神职身份（需要策略考虑）
3. 与狼队友配合，但必要时可以切割队友
4. 分析神职玩家的行为，优先击杀威胁

伪装策略：
- 表现出寻找狼人的积极态度
- 可以质疑预言家，但不要过于明显
- 队友被查杀时，评估是否需要弃车保帅
- 投票时要表现出好人的思维逻辑"""

        else:
            return "请按照你的角色进行游戏。"
    
    def _build_full_prompt(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Build the full prompt with context"""
        full_prompt = prompt
        
        if context:
            # Add speaking order context for day discussions
            if "speaking_context" in context:
                speaking = context["speaking_context"]
                full_prompt += f"\n\n=== 发言顺序信息 ==="
                full_prompt += f"\n- 你的发言顺序：第{speaking.get('my_position', 0)}位"
                before_players = [f"{p['name']}({p['id']})" for p in speaking.get('players_before_me', [])]
                after_players = [f"{p['name']}({p['id']})" for p in speaking.get('players_after_me', [])]
                full_prompt += f"\n- 已发言玩家：{before_players or '无'}"
                full_prompt += f"\n- 未发言玩家：{after_players or '无'}"
                full_prompt += f"\n- 重要提醒：{speaking.get('strict_warning', '')}"
            
            full_prompt += f"\n\n🎯 当前游戏状态："
            if "game_state" in context:
                game_state = context["game_state"]
                current_round = game_state.get('round', 0)
                current_phase = game_state.get('phase', '未知')
                full_prompt += f"\n- 📅 当前轮次：第{current_round}轮"
                full_prompt += f"\n- 🕐 当前阶段：{current_phase}"
                full_prompt += f"\n- ✅ 存活的玩家：{game_state.get('alive_players', [])}"
                full_prompt += f"\n- ❌ 死亡的玩家：{game_state.get('dead_players', [])}"
                
                # 添加轮次提醒
                if current_round == 1:
                    full_prompt += f"\n- ⚠️ 第一轮提醒：这是游戏开始，没有历史信息可参考"
                elif current_round == 2:
                    full_prompt += f"\n- ⚠️ 第二轮提醒：可以参考第一轮的发言和投票结果"
                else:
                    full_prompt += f"\n- ⚠️ 第{current_round}轮提醒：可以参考前{current_round-1}轮的所有信息"
            
            if "night_events" in context:
                night_events = context["night_events"]
                full_prompt += f"\n- 昨夜事件：{night_events}"
            
            # Add strict speaking order rules for day phase
            if context.get("game_state", {}).get("phase") == "day":
                full_prompt += f"\n\n=== 发言规则提醒 ==="
                full_prompt += f"\n⚠️ 严格规则："
                full_prompt += f"\n1. 只能分析已经发言的玩家"
                full_prompt += f"\n2. 不能提及未发言玩家的观点或行为"
                full_prompt += f"\n3. 使用'根据前面发言'、'从已发言玩家来看'等限定词"
                full_prompt += f"\n4. 避免绝对判断，使用'可能'、'倾向于'等表述"
            
            if "discussion" in context:
                full_prompt += f"\n- 当前讨论：{context['discussion']}"
        
        return full_prompt
    
    def vote_for_player(self, candidates: List[int], reason: str = None, context: Dict[str, Any] = None) -> int:
        """Ask the LLM to vote for a player with strategic analysis"""
        # Remove self from candidates if present
        safe_candidates = [c for c in candidates if c != self.id]
        if not safe_candidates:
            return candidates[0] if candidates else self.id
        
        # Build strategic voting context
        strategic_context = self._build_voting_context()
        
        # Add day speeches and last words to voting context
        day_speeches_context = ""
        if context and context.get("all_day_speeches"):
            day_speeches_context = "\n\n=== 今日所有发言记录 ==="
            for speech in context["all_day_speeches"]:
                player_name = speech.get("name", f"玩家{speech.get('player', '?')}")
                player_id = speech.get("player", "?")
                speech_content = speech.get("speech", "")
                day_speeches_context += f"\n• {player_name}({player_id}): {speech_content}"
        
        last_words_context = ""
        if context and context.get("last_words_for_voting"):
            last_words_context = "\n\n🔥🔥🔥 关键遗言信息（投票决策的重要依据）🔥🔥🔥"
            for lw in context["last_words_for_voting"]:
                player_name = lw.get("name", f"玩家{lw.get('player', '?')}")
                player_id = lw.get("player", "?")
                speech = lw.get("speech", "")
                last_words_context += f"\n📢 死亡玩家{player_name}({player_id})的完整遗言：\n   「{speech}」"
            last_words_context += "\n\n⚠️ 投票提醒：如果遗言中有预言家查杀信息，这是最可靠的投票依据！"
        
        # 添加预言家保护检查 - 基于历史查杀记录
        seer_protection_warning = ""
        proven_seer_candidates = []
        
        if (self.team.value if hasattr(self.team, 'value') else self.team) == "villager":
            # 检查候选人中是否有已证明身份的预言家
            for candidate in safe_candidates:
                # 检查是否有玩家声称是预言家且有成功查杀记录
                if context and context.get("all_day_speeches"):
                    for speech in context["all_day_speeches"]:
                        if speech.get("player") == candidate:
                            speech_content = speech.get("speech", "")
                            # 检查是否声称预言家且有查杀信息
                            if ("我是预言家" in speech_content or "预言家" in speech_content) and "查验" in speech_content:
                                # 检查是否有成功的查杀记录（被查杀的玩家确实被投票淘汰）
                                if context.get("dead_players"):
                                    for dead_player in context["dead_players"]:
                                        if "werewolf" in str(dead_player) and "查杀" in speech_content:
                                            proven_seer_candidates.append(candidate)
                                            break
            
            # 如果发现已证明身份的预言家在候选人中，发出警告
            for proven_seer in proven_seer_candidates:
                if proven_seer in safe_candidates:
                    seer_protection_warning = f"""
🚨🚨🚨 致命错误警告 🚨🚨🚨
玩家{proven_seer}是已经通过成功查杀证明身份的真预言家！
该玩家在前面轮次查杀的狼人已被证实并投票淘汰！
作为好人阵营，投票给真预言家等于自杀！
好人阵营失去预言家就等于失败！
你必须立即从投票目标中排除玩家{proven_seer}！
"""
                    safe_candidates = [c for c in safe_candidates if c != proven_seer]

        prompt = f"""=== 投票阶段战略分析 ===

{seer_protection_warning}

{strategic_context}{day_speeches_context}{last_words_context}

可选投票目标：{safe_candidates}

=== 投票策略指导 ===
作为{self.team.value if hasattr(self.team, 'value') else self.team}阵营，你需要基于以下原则投票：

{"**狼人投票策略：**" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "**好人投票策略：**"}
{"- 避免投票给狼队友，优先投票给神职玩家" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "- 🚨 绝对禁止投票淘汰已证明身份的真预言家！"}
{"- 制造混乱，质疑预言家的可信度" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "- 优先相信预言家的查杀信息，如果预言家报出查杀且无对跳，必须高度相信"}
{"- 伪装成好人，表现出合理的推理逻辑" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "- 预言家查杀的玩家是第一投票目标，其他分析都是次要的"}

=== 关键判断原则 ===
1. **预言家查杀的可信度**：如果有预言家明确报出查杀，且无其他玩家对跳预言家，这个查杀信息极其可靠
2. **预言家保护原则**：真预言家是好人阵营最重要的信息来源，绝对不能投票淘汰真预言家
3. **对跳判断**：只有当出现多个预言家对跳时，才需要判断真假；单独跳预言家且有查杀的，应该高度相信
4. **发言逻辑分析**：观察玩家发言是否符合其声称的身份，是否有逻辑矛盾
5. **行为动机分析**：好人发言是为了找狼，狼人发言是为了混淆视听
6. **投票行为分析**：观察谁在为被查杀的玩家辩护，这些人可能是狼队友

请严格按照以下格式回复：
VOTE: [玩家ID]
REASON: [详细的投票理由，必须基于具体的游戏信息和策略分析]

示例回复：
VOTE: 3
REASON: 预言家明确查杀了玩家3，且无其他玩家对跳预言家，这个查杀信息可信度极高。玩家3在发言中试图质疑预言家，这种行为符合被查杀狼人的典型反应。
"""
        response = self.send_message(prompt)
        # print(f"投票阶段 - {self.name}({self.id}) 的投票决策：{response}")  # 简化投票输出
        
        try:
            # Parse structured response
            lines = response.strip().split('\n')
            vote_target = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('VOTE:'):
                    target_str = line.split(':', 1)[1].strip()
                    if target_str.isdigit():
                        vote_target = int(target_str)
            
            if vote_target and vote_target in safe_candidates:
                print(f"✅ {self.name}({self.id}) 投票给玩家 {vote_target}")
                return vote_target
                
        except Exception as e:
            print(f"解析投票失败：{e}")
        
        # Fallback to simple parsing
        try:
            import re
            numbers = re.findall(r'\d+', response)
            for num in numbers:
                if int(num) in safe_candidates:
                    print(f"✅ {self.name}({self.id}) 投票给玩家 {num}（回退解析）")
                    return int(num)
        except:
            pass
        
        # Default to first safe candidate
        if safe_candidates:
            target = safe_candidates[0]
            print(f"⚠️ {self.name}({self.id}) 默认投票给玩家 {target}")
            return target
        
        return candidates[0] if candidates else self.id
    
    def _build_voting_context(self) -> str:
        """Build strategic voting context based on game information"""
        context_parts = []
        
        # Add seer check information if available
        if self.role == Role.SEER and self.seer_checks:
            context_parts.append("=== 预言家查验信息 ===")
            for player_id, result in self.seer_checks.items():
                context_parts.append(f"- 玩家{player_id}: {result}")
        
        # Add general strategic context
        context_parts.append("=== 当前局面分析 ===")
        context_parts.append("- 分析已发言玩家的逻辑一致性")
        context_parts.append("- 观察是否有预言家跳出并报查杀")
        context_parts.append("- 注意是否有玩家为被查杀者辩护")
        context_parts.append("- 考虑发言动机：好人找狼 vs 狼人混淆")
        
        if self.team == "villager":
            context_parts.append("\n=== 好人阵营铁律 ===")
            context_parts.append("- 🚨🚨🚨 绝对禁令：永远不能投票淘汰真预言家！这是好人阵营的死亡行为！")
            context_parts.append("- 🔥 预言家查杀信息是最高优先级：如果预言家报查杀且无对跳，必须无条件相信")
            context_parts.append("- ⚡ 投票优先级：被查杀的狼人 > 其他可疑玩家 > 绝不投预言家")
            context_parts.append("- 🛡️ 预言家保护：预言家是好人阵营唯一的信息来源，失去预言家=失败")
            context_parts.append("- ❌ 严禁行为：质疑已证明身份的预言家、投票给跳预言家的玩家")
            context_parts.append("- ✅ 正确做法：跟随预言家指挥，投票给被查杀的狼人")
        else:
            context_parts.append("\n=== 狼人阵营高级策略 ===")
            context_parts.append("- **弃车保帅判断**：如果队友被预言家查杀且无法反驳，评估是否需要切割")
            context_parts.append("- **票数对比分析**：计算狼队vs好人的票数，如果明显处于劣势则考虑放弃队友")
            context_parts.append("- **暴露风险评估**：如果继续为队友辩护会暴露自己，果断投票给队友")
            context_parts.append("- **团队利益优先**：保护未暴露的队友比救一个暴露的队友更重要")
            context_parts.append("- **伪装好人思维**：投票给暴露队友时要表现出'正义'的好人逻辑")
            context_parts.append("- **避免过度辩护**：适度质疑预言家可以，但不要成为唯一为队友说话的人")
        
        return "\n".join(context_parts)
    
    def make_night_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle night actions based on role"""
        if not self.is_alive():
            return {}
        
        if self.role == Role.WEREWOLF:
            return self._werewolf_action(context)
        elif self.role == Role.SEER:
            return self._seer_action(context)
        elif self.role == Role.WITCH:
            return self._witch_action(context)
        elif self.role == Role.HUNTER:
            return self._hunter_action(context)
        
        return {}
    
    def _hunter_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Hunter action - decide whether to shoot when killed"""
        # Hunter doesn't have night actions, only day actions when killed
        return {}
    
    def _werewolf_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wolf team coordination - unified decision making"""
        # print(f"🔍 DEBUG: _werewolf_action called")
        # print(f"🔍 DEBUG: context keys: {list(context.keys())}")
        
        alive_players = context.get("alive_players", [])
        wolf_team = context.get("wolf_team", [])
        
        # print(f"🔍 DEBUG: alive_players: {alive_players}, type: {type(alive_players)}")
        # print(f"🔍 DEBUG: wolf_team: {wolf_team}, type: {type(wolf_team)}")
        
        # Extract wolf IDs from the new format
        wolf_ids = [w.get("id") if isinstance(w, dict) else w for w in wolf_team]
        # print(f"🔍 DEBUG: extracted wolf_ids: {wolf_ids}")
        
        # Extract non-wolf player IDs (integers only)
        try:
            if alive_players and isinstance(alive_players[0], dict):
                # New format: alive_players is list of dicts
                non_wolf_players = [p["id"] for p in alive_players if p["id"] not in wolf_ids]
            else:
                # Old format: alive_players is list of integers
                non_wolf_players = [p for p in alive_players if p not in wolf_ids]
            # print(f"🔍 DEBUG: non_wolf_players: {non_wolf_players}")
        except Exception as e:
            print(f"🚨 ERROR in non_wolf_players calculation: {e}")
            print(f"🚨 ERROR: alive_players type: {type(alive_players)}, items: {alive_players}")
            print(f"🚨 ERROR: wolf_ids type: {type(wolf_ids)}, items: {wolf_ids}")
            raise
        
        if not non_wolf_players:
            # print("🔍 DEBUG: No non-wolf players available")
            return {}
        
        # Get player names for display
        player_names = {}
        players_data = context.get("game_state", {}).get("players", {})
        
        if isinstance(players_data, dict):
            # New format: players is dict with ID keys
            for pid in non_wolf_players:
                player_info = players_data.get(pid, {})
                if isinstance(player_info, dict):
                    player_names[pid] = player_info.get("name", f"玩家{pid}")
                else:
                    player_names[pid] = f"玩家{pid}"
        else:
            # Fallback for any other format
            for pid in non_wolf_players:
                player_names[pid] = f"玩家{pid}"
        
        # Wolf team context - all wolves see the same info
        # Get target names from context
        target_info = context.get("target_info", [])
        target_names = {}
        for target in target_info:
            target_names[target["id"]] = target["name"]
        
        prompt = f"""🐺 狼人团队夜间会议 - 第{context.get('game_state', {}).get('round', 1)}轮

你是狼人团队的一员。当前狼人团队成员：{[f"玩家{wid}" for wid in wolf_team]}

可选击杀目标（都是好人身份）：
"""
        for pid in non_wolf_players:
            name = target_names.get(pid, f"玩家{pid}")
            prompt += f"- {name}({pid})\n"
        
        prompt += f"""
作为狼人团队，你们需要统一选择一个目标进行击杀。请你基于玩家的发言，确认最优先的击杀目标。

请严格按照以下格式回复：
KILL: [玩家ID]
REASON: [选择该玩家的团队策略原因]

示例：
KILL: 5
REASON: 该玩家白天表现可疑，可能是神职，优先击杀

狼人团队必须达成一致击杀目标。"""
        
        response = self.send_message(prompt, context)
        # print(f"🐺 狼人 {self.name}({self.id}) 的击杀选择：{response}")
        
        # Strict parsing
        try:
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('KILL:'):
                    target_str = line.split(':', 1)[1].strip()
                    if target_str.isdigit():
                        target = int(target_str)
                        if target in non_wolf_players:
                            # print(f"✅ 狼人 {self.name}({self.id}) 选择击杀玩家 {target}")
                            return {"action": "kill", "target": target, "wolf_id": self.id}
        except Exception as e:
            # print(f"解析狼人选择失败：{e}")
            pass
        
        # Force selection
        target = non_wolf_players[0]
        # print(f"⚠️ 狼人 {self.name}({self.id}) 强制选择击杀玩家 {target}")
        return {"action": "kill", "target": target, "wolf_id": self.id}
    
    def _hunter_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Hunter action - decide whether to shoot when killed"""
        # Hunter doesn't have night actions, only day actions when killed
        return {}
    
    def _seer_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Seer night action - check a player's identity with strict format"""
        # Handle both old and new context formats
        if "context_type" in context and context["context_type"] == "seer_private":
            # New format from get_context_for_player
            unchecked_info = context.get("unchecked_players", [])
            unchecked_players = [p["id"] for p in unchecked_info]
            
            if not unchecked_players:
                print(f"🔄 预言家 {self.name}({self.id}) 已查验所有玩家")
                return {"action": "none"}
            
            # Build display from context
            display_targets = [(p["id"], p["name"]) for p in unchecked_info]
            checked_players = context.get("seer_checks", {})
        else:
            # Old format from direct context
            alive_players = context.get("alive_players", [])
            unchecked_players = [p for p in alive_players if p != self.id and p not in self.seer_checks]
            
            if not unchecked_players:
                print(f"🔄 预言家 {self.name}({self.id}) 已查验所有玩家")
                return {"action": "none"}
            
            # Get player names
            player_names = {}
            game_state = context.get("game_state", {})
            players_data = game_state.get("players", {})
            
            for pid in unchecked_players:
                if isinstance(players_data, dict):
                    player_data = players_data.get(pid, {})
                    player_names[pid] = player_data.get("name", f"玩家{pid}")
                else:
                    player_names[pid] = f"玩家{pid}"
            
            display_targets = [(pid, player_names.get(pid, f"玩家{pid}")) for pid in unchecked_players]
            checked_players = self.seer_checks
        
        prompt = f"""🔮 预言家夜间行动 - 第{self.game_state.current_round if hasattr(self, 'game_state') else 1}轮

你是预言家，必须选择一名玩家进行身份查验。你的目标是找出狼人并为好人阵营提供关键信息。

可选查验目标：
"""
        for pid, name in display_targets:
            prompt += f"- {name}({pid})\n"
        
        prompt += f"""
已查验记录：{list(checked_players.keys()) or '无'}

查验策略建议：
1. 优先查验发言激进或行为可疑的玩家
2. 查验高威胁目标（可能的神职或关键玩家）
3. 考虑查验发言逻辑矛盾的玩家

必须严格按照以下格式回复：
CHECK: [玩家ID]
REASON: [选择该玩家的策略原因]

示例：
CHECK: 5
REASON: 该玩家白天发言逻辑矛盾，对狼人行为分析过于详细，疑似狼人

你必须选择一个玩家进行查验，并给出明确的策略理由。"""
        
        response = self.send_message(prompt, context)
        # print(f"🔮 预言家 {self.name}({self.id}) 的查验决策：{response}")
        
        # Strict parsing - must return a valid target
        try:
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('CHECK:'):
                    target_str = line.split(':', 1)[1].strip()
                    if target_str.isdigit():
                        target = int(target_str)
                        if target in [t[0] for t in display_targets]:
                            # print(f"✅ 预言家 {self.name}({self.id}) 选择查验玩家 {target}")
                            return {"action": "check", "target": target}
        except Exception as e:
            # print(f"解析预言家查验失败：{e}")
            pass
        
        # Force selection of first available player
        target = display_targets[0][0]
        # print(f"⚠️ 预言家 {self.name}({self.id}) 强制选择查验玩家 {target}")
        return {"action": "check", "target": target}
    
    def _hunter_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Hunter action - decide whether to shoot when killed"""
        # Hunter doesn't have night actions, only day actions when killed
        return {}
        
        prompt = f"""作为预言家，请选择今晚要查验的玩家。

可选玩家：{unchecked_players}

请严格按照以下格式回复：
ACTION: check
TARGET: [玩家ID]
REASON: [选择该玩家的原因]

示例回复：
ACTION: check
TARGET: 7
REASON: 该玩家白天发言积极，需要确认身份
"""
        response = self.send_message(prompt, context)
        print(f"预言家 {self.name}({self.id}) 的查验决策：{response}")
        
        try:
            # Parse structured response
            lines = response.strip().split('\n')
            action = ""
            target = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('ACTION:'):
                    action = line.split(':', 1)[1].strip().lower()
                elif line.startswith('TARGET:'):
                    target_str = line.split(':', 1)[1].strip()
                    if target_str.isdigit():
                        target = int(target_str)
            
            if action == "check" and target and target in unchecked_players:
                return {"action": "check", "target": target}
                
        except Exception as e:
            print(f"解析预言家决策失败：{e}")
        
        # Fallback to simple parsing
        try:
            import re
            numbers = re.findall(r'\d+', response)
            for num in numbers:
                if int(num) in unchecked_players:
                    print(f"预言家 {self.name}({self.id}) 选择查验玩家 {num}")
                    return {"action": "check", "target": int(num)}
        except:
            pass
        
        # Default to first unchecked player
        if unchecked_players:
            target = unchecked_players[0]
            print(f"预言家 {self.name}({self.id}) 默认选择查验玩家 {target}")
            return {"action": "check", "target": target}
        
        return {}
    
    def _hunter_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Hunter action - decide whether to shoot when killed"""
        # Hunter doesn't have night actions, only day actions when killed
        return {}
    
    def _witch_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Witch night action - private potion decision"""
        
        # Initialize variables for both formats
        killed_player = None
        display_targets = []
        has_heal = False
        has_poison = False
        player_names = {}

        # Handle both context formats
        if "context_type" in context and context["context_type"] == "witch_private":
            # New format from get_context_for_player
            killed_info = context.get("killed_player")
            if killed_info:
                if isinstance(killed_info, dict):
                    killed_player = killed_info["id"]
                else:
                    killed_player = killed_info
            
            poison_targets_info = context.get("poison_targets", [])
            display_targets = [(p["id"], p["name"]) for p in poison_targets_info]
            has_heal = context.get("heal_potion", False)
            has_poison = context.get("poison_potion", False)
            
            # Build player names from poison_targets
            for p in poison_targets_info:
                player_names[p["id"]] = p["name"]
        else:
            # Old format - use actual player object state
            alive_players = context.get("alive_players", [])
            
            # Get player names
            game_state = context.get("game_state", {})
            players_data = game_state.get("players", {})
            
            for pid in alive_players:
                if pid != self.id:
                    if isinstance(players_data, dict):
                        player_data = players_data.get(pid, {})
                        player_names[pid] = player_data.get("name", f"玩家{pid}")
                    else:
                        player_names[pid] = f"玩家{pid}"
            
            display_targets = [(pid, player_names.get(pid, f"玩家{pid}")) 
                              for pid in alive_players if pid != self.id]
            
            # Always use actual player object state for potions
            has_heal = self.witch_potions.get("heal", False)
            has_poison = self.witch_potions.get("poison", False)
        
        prompt = f"""🧙‍♀️ 女巫的私人夜间决策 - 第{context.get('game_state', {}).get('round', 1)}轮

当前状态：
- 解药：{'可用' if has_heal else '已用完'}
- 毒药：{'可用' if has_poison else '已用完'}
"""
        
        if killed_player:
            killed_name = player_names.get(killed_player, f"玩家{killed_player}")
            prompt += f"- 今晚被狼人击杀的玩家：{killed_name}({killed_player})\n"
        
        prompt += f"\n可选毒药目标：\n"
        for pid, name in display_targets:
            prompt += f"- {name}({pid})\n"
        
        prompt += f"""
作为女巫，你必须做出以下选择之一：

1. 使用解药救今晚被击杀的玩家（如果有且你有解药）
2. 使用毒药毒杀一名玩家（如果你有毒药）
3. 不使用任何药物

必须严格按照以下格式回复：
ACTION: [heal/poison/none]
TARGET: [玩家ID或空]

示例1（使用解药）：
ACTION: heal
TARGET: {killed_player or '3'}

示例2（使用毒药）：
ACTION: poison
TARGET: 7

示例3（不使用）：
ACTION: none
TARGET: 

你必须做出选择，不能跳过。"""
        
        response = self.send_message(prompt, context)
        print(f"🧙‍♀️ 女巫 {self.name}({self.id}) 的私人决策：{response}".replace('\n', ''))
        
        # Strict parsing
        try:
            lines = response.strip().split('\n')
            action = ""
            target = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('ACTION:'):
                    action = line.split(':', 1)[1].strip().lower()
                elif line.startswith('TARGET:'):
                    target_str = line.split(':', 1)[1].strip()
                    if target_str.isdigit():
                        target = int(target_str)
            
            # Validate action with correct potion check
            actual_has_heal = self.witch_potions.get("heal", False)
            actual_has_poison = self.witch_potions.get("poison", False)
            
            # print(f"🔍 DEBUG: Witch potion check - heal: {actual_has_heal}, poison: {actual_has_poison}")
            
            if action == "heal" and killed_player is not None and actual_has_heal:
                print(f"✅ 女巫 {self.name}({self.id}) 决定使用解药救 {killed_player}")
                # 不在这里修改状态，让night_phase.py统一处理
                return {"action": "heal", "target": killed_player}
            elif action == "poison" and target and actual_has_poison:
                target_in_list = any(t[0] == target for t in display_targets)
                if target_in_list and target != self.id:
                    print(f"✅ 女巫 {self.name}({self.id}) 决定使用毒药毒 {target}")
                    # 不在这里修改状态，让night_phase.py统一处理
                    return {"action": "poison", "target": target}
            elif action == "none":
                print(f"✅ 女巫 {self.name}({self.id}) 选择不使用药物")
                return {"action": "none"}
                
        except Exception as e:
            print(f"解析女巫决策失败：{e}")
        
        # Force none action as fallback
        print(f"⚠️ 女巫 {self.name}({self.id}) 默认选择不使用药物")
        return {"action": "none"}
    
    def speak(self, context: Dict[str, Any]) -> str:
        """Generate speech for day discussion with enhanced hallucination detection and correction"""
        
        # Initialize legacy validator for backward compatibility
        validator = RealityConstraintValidator(self.game_state if hasattr(self, 'game_state') else None)
        
        # Build enhanced context using the new context builder
        try:
            if hasattr(self, 'context_builder') and hasattr(context, 'get') and 'game_state' in context:
                # Get speech tracker from game state if available
                game_state = context.get('game_state')
                speech_tracker = getattr(game_state, 'speech_history_tracker', None)
                
                if speech_tracker:
                    enhanced_context = self.context_builder.build_context(
                        self.id, 
                        context.get('phase', 'day'), 
                        game_state,
                        speech_tracker
                    )
                    # Merge enhanced context with original context
                    context.update(enhanced_context)
        except Exception as e:
            print(f"Warning: Enhanced context building failed: {e}")
            # Continue with original context
        
        # Get speaking order information from day context
        players_before = [p["name"] for p in context.get("players_before_me", [])]
        players_after = [p["name"] for p in context.get("players_after_me", [])]
        my_position = context.get("my_position", 1)
        
        # Build actual speech context
        speech_context = []
        if players_before:
            speech_context.append(f"已发言玩家：{', '.join(players_before)}")
        if players_after:
            speech_context.append(f"待发言玩家：{', '.join(players_after)}")
        speech_context.append(f"你的发言顺序：第{my_position}位")
        
        # Add last words information if available
        last_words_info = ""
        last_words = context.get("last_words") or context.get("available_last_words", [])
        if last_words:
            last_words_info = "\n\n🔥🔥🔥 重要遗言信息（必须仔细阅读，不要理解错误）🔥🔥🔥："
            for lw in last_words:
                player_name = lw.get("name") or lw.get("player_name", f"玩家{lw.get('player', lw.get('player_id', '?'))}")
                player_id = lw.get("player") or lw.get("player_id", "?")
                speech = lw.get("speech") or lw.get("last_words", "")
                last_words_info += f"\n📢 死亡玩家{player_name}({player_id})的完整遗言内容：\n   「{speech}」"
            last_words_info += "\n\n⚠️⚠️⚠️ 重要提醒：请仔细阅读遗言的具体内容，不要误解或编造遗言中没有的信息！⚠️⚠️⚠️"
            last_words_info += "\n💡 如果遗言中提到查杀某个玩家，请准确记住是哪个玩家被查杀！"
            last_words_info += "\n🚫 绝对不要说遗言中查杀了你自己，除非遗言明确提到你的编号！"
        
        # Add historical context information if available
        historical_info = ""
        historical_context = context.get("historical_context", {})
        if historical_context.get("has_history"):
            historical_info = "\n\n📚 历史游戏信息（重要参考）："
            
            # 添加历史遗言
            if historical_context.get("all_last_words"):
                historical_info += "\n\n🗣️ 历史遗言记录："
                for hw in historical_context["all_last_words"]:
                    round_num = hw.get("round", "?")
                    player_name = hw.get("player_name", "?")
                    player_id = hw.get("player_id", "?")
                    last_words = hw.get("last_words", "")
                    historical_info += f"\n  第{round_num}轮 - {player_name}({player_id}): {last_words}"
            
            # 添加历史发言记录
            if historical_context.get("previous_rounds"):
                historical_info += "\n\n💬 历史发言记录："
                for round_data in historical_context["previous_rounds"]:
                    round_num = round_data.get("round", "?")
                    speeches = round_data.get("speeches", [])
                    historical_info += f"\n  第{round_num}轮发言 ({len(speeches)}条):"
                    for speech in speeches:  # 只显示前3条发言
                        player_name = speech.get("player_name", "?")
                        content = speech.get("speech", "")
                        historical_info += f"\n    - {player_name}: {content}"
            
            # 添加投票历史
            if historical_context.get("voting_history"):
                historical_info += "\n\n🗳️ 历史投票记录："
                for vote_record in historical_context["voting_history"]:
                    round_num = vote_record.get("round", "?")
                    eliminated_name = vote_record.get("eliminated_name", "无人")
                    historical_info += f"\n  第{round_num}轮: {eliminated_name}被淘汰"
            
            historical_info += "\n\n💡 请结合历史信息和当前情况进行综合分析！"
        
        # Role-specific speech constraints
        role_constraints = """
⚠️ 村民特殊注意：
- 必须表明自己的好人身份
- 根据场上情况，可以在发言时伪装为预言家或女巫或猎人，为他们挡刀
- 游戏规则无警徽，请绝对避免提及警徽流
- 发言要有逻辑性"""
        if self.role == Role.WEREWOLF:
            role_constraints = """
⚠️ 狼人特殊注意：
- 绝对不能透露自己是狼人
- 必须假装是好人阵营
- 根据场上情况，甚至可以在发言时伪装为预言家或女巫或猎人
- 发言要有逻辑性，避免暴露狼队信息"""
        elif self.role == Role.SEER:
            role_constraints = """
⚠️ 预言家特殊注意：
- 可以基于查验结果透露自己是预言家
- 可以基于查验结果做隐晦分析
- 在需要展示身份时，明确表达自己是预言家
- 避免暴露查验顺序"""
        elif self.role == Role.WITCH:
            role_constraints = """
⚠️ 女巫特殊注意：
- 可以基于用药情况透露自己是女巫
- 避免提及药物使用情况
- 可以基于救人/毒人信息做分析"""
        elif self.role == Role.HUNTER:
            role_constraints = """
⚠️ 猎人特殊注意：
- 可以基于场面情况明确表示自己是猎人
- 避免提及开枪能力"""
        
        # Special handling for seer's last words
        is_last_words = context.get("is_last_words", False)
        death_reason = context.get("death_reason", "")
        
        if self.role == Role.SEER and is_last_words:
            # Seer must reveal check results in last words
            prompt = f"""这是你的遗言！作为预言家，你必须立即公开所有查验结果。

=== 遗言环境 ===
- 你已被{death_reason}
- 这是你的遗言，必须公开所有查验信息
- 你的查验记录：{json.dumps(self.seer_checks, ensure_ascii=False, indent=2)}

=== 遗言要求 ===
请严格按照以下格式回复：

LAST_WORDS: [你的遗言内容]

遗言内容必须包含：
1. 明确声明自己是预言家
2. 公开所有查验结果（查验的编号和查出的身份）
3. 给出下一步好人阵营的建议

示例遗言：
LAST_WORDS: 我是预言家，我查验了编号3是狼人，编号5是好人。根据查验结果，编号3肯定是狼人，建议好人优先投票淘汰他。

请发表你的遗言："""
        else:
            prompt = f"""请发表你的看法和推理。严格遵守以下规则和格式：

=== 当前发言环境 ===
- 你是第{my_position}个发言的玩家
{chr(10).join(f'- {item}' for item in speech_context)}{last_words_info}{historical_info}

=== 身份限制 ==={role_constraints}

=== 发言格式要求 ===
请严格按照以下格式回复：

SPEECH: [你的发言内容]

发言内容要求：
1. **必须明确提及你是第几个发言**（例如："我是第{my_position}个发言"）
2. **必须基于已发言玩家的内容**做分析
3. **如果有遗言信息，必须重点分析遗言内容**
4. **重要：不要混淆发言顺序和玩家编号！你是{self.name}({self.id})，第{my_position}个发言**
5. **如果遗言提到查杀某个编号的玩家，请准确记住是哪个编号，不要与自己的编号混淆**
6. **不能提及未发言玩家的任何信息**
7. **不要分点描述，使用一句400字以内的话完成自己的发言**
8. **使用逻辑推理而非主观猜测**
9. **避免绝对判断，使用"可能"、"倾向于"等表述**
10. **当你还不想暴露你的身份时，不要在发言内容中提及你的身份；当你想展现你的身份时，明确的在发言内容中说明**
11. **语气可以更活泼**

示例发言：
SPEECH: 我是第{my_position}个发言，我是{self.name}，我的编号是{self.id}。根据前面张三的发言，我认为他的逻辑有些问题。他说自己是村民，但是对狼人行为的分析过于详细，这让我有些怀疑。不过这只是初步判断，还需要更多信息。

请开始你的发言："""
        
        response = self.send_message(prompt, context)
        
        # Extract only the SPEECH content
        initial_speech = ""
        try:
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('SPEECH:'):
                    initial_speech = line.split(':', 1)[1].strip()
                    break
            
            # If no SPEECH tag found, use the full response
            if not initial_speech:
                initial_speech = response
                
        except:
            initial_speech = response
        
        # Enhanced hallucination detection using multi-layer system
        try:
            if hasattr(self, 'hallucination_detector') and hasattr(context, 'get') and 'game_state' in context:
                game_state = context.get('game_state')
                speech_tracker = getattr(game_state, 'speech_history_tracker', None)
                
                if speech_tracker:
                    # Use enhanced multi-layer hallucination detection
                    hallucination_result = self.hallucination_detector.detect_all_hallucinations(
                        initial_speech, self, context, speech_tracker
                    )
                    
                    print(f"🔍 Enhanced Detection - {self.name}({self.id}): {hallucination_result.hallucination_count} hallucinations detected")
                    
                    if not hallucination_result.is_valid and hallucination_result.correction_needed:
                        print(f"🚨 Enhanced hallucination detection - {self.name}({self.id}): {len(hallucination_result.hallucinations)} issues")
                        
                        # Use enhanced speech corrector
                        correction_result = self.speech_corrector.correct_speech(
                            initial_speech, hallucination_result.hallucinations, context, self
                        )
                        
                        if correction_result.success:
                            print(f"✅ Enhanced correction applied - {self.name}({self.id})")
                            print(f"   Quality score: {correction_result.quality_score:.2f}")
                            print(f"   Corrections: {len(correction_result.corrections_applied)}")
                            
                            # Log enhanced detection and correction
                            self._log_enhanced_hallucination_detection(initial_speech, hallucination_result, correction_result, context)
                            
                            return correction_result.corrected_speech
                        else:
                            print(f"⚠️ Enhanced correction failed - {self.name}({self.id}), falling back to legacy system")
                    else:
                        # Log successful validation
                        self._log_enhanced_speech_quality(initial_speech, hallucination_result, context)
                        return initial_speech
        except Exception as e:
            print(f"Warning: Enhanced hallucination detection failed: {e}, falling back to legacy system")
        
        # Fallback to legacy validation system
        validation_result = validator.validate_speech_content(
            self.id, 
            self.role, 
            initial_speech, 
            context
        )
        
        # Log speech quality and hallucination detection
        quality_score = self._evaluate_speech_quality(initial_speech, validation_result, context)
        self._log_speech_quality(initial_speech, validation_result, quality_score, context)
        
        if not validation_result["is_valid"]:
            print(f"🚨 Legacy detection - {self.name}({self.id}): {validation_result['issues']}")
            
            # Log hallucination detection
            self._log_hallucination_detection(initial_speech, validation_result, context)
            
            # Use corrected speech
            corrected_speech = validation_result["corrected_speech"]
            print(f"✅ Legacy correction - {self.name}({self.id}): {corrected_speech}")
            
            # Log correction history
            self._log_correction_history(initial_speech, corrected_speech, validation_result["issues"], context)
            
            return corrected_speech
        
        return initial_speech
    
    def _log_enhanced_hallucination_detection(
        self, 
        original_speech: str, 
        hallucination_result: Any, 
        correction_result: Any, 
        context: Dict[str, Any] = None
    ):
        """Log enhanced hallucination detection results"""
        enhanced_log = {
            "timestamp": "current",
            "round": context.get("round", 1) if context else 1,
            "player_id": self.id,
            "player_name": self.name,
            "original_speech": original_speech,
            "hallucination_count": hallucination_result.hallucination_count,
            "confidence_score": hallucination_result.confidence_score,
            "correction_needed": hallucination_result.correction_needed,
            "correction_success": correction_result.success,
            "correction_quality": correction_result.quality_score,
            "corrections_applied": len(correction_result.corrections_applied),
            "hallucination_types": [h.type.value for h in hallucination_result.hallucinations],
            "correction_types": [c.type.value for c in correction_result.corrections_applied],
            "system_version": "enhanced"
        }
        
        self.hallucination_detection_log.append(enhanced_log)
    
    def _log_enhanced_speech_quality(
        self, 
        speech: str, 
        hallucination_result: Any, 
        context: Dict[str, Any] = None
    ):
        """Log enhanced speech quality for valid speeches"""
        quality_log = {
            "timestamp": "current",
            "round": context.get("round", 1) if context else 1,
            "player_id": self.id,
            "player_name": self.name,
            "speech": speech,
            "quality_score": hallucination_result.confidence_score,
            "is_valid": hallucination_result.is_valid,
            "issues_count": hallucination_result.hallucination_count,
            "speech_length": len(speech),
            "system_version": "enhanced"
        }
        
        self.speech_quality_log.append(quality_log)
    
    def _evaluate_speech_quality(self, speech: str, validation_result: Dict[str, Any], context: Dict[str, Any] = None) -> float:
        """评估发言质量，返回0-1之间的分数"""
        score = 1.0
        
        # 基于幻觉检测结果扣分
        if not validation_result["is_valid"]:
            issue_count = len(validation_result["issues"])
            score -= min(0.5, issue_count * 0.1)  # 每个问题扣0.1分，最多扣0.5分
        
        # 基于发言长度评估
        if len(speech) < 20:
            score -= 0.2  # 发言过短扣分
        elif len(speech) > 500:
            score -= 0.1  # 发言过长轻微扣分
        
        # 基于第一轮特殊要求评估
        if context and context.get("round", 1) == 1:
            if "我是第" not in speech:
                score -= 0.1  # 第一轮未明确发言顺序
        
        return max(0.0, score)
    
    def _log_speech_quality(self, speech: str, validation_result: Dict[str, Any], quality_score: float, context: Dict[str, Any] = None):
        """记录发言质量日志"""
        quality_log = {
            "timestamp": "current",
            "round": context.get("round", 1) if context else 1,
            "player_id": self.id,
            "player_name": self.name,
            "speech": speech,
            "quality_score": quality_score,
            "is_valid": validation_result["is_valid"],
            "issues_count": len(validation_result["issues"]),
            "speech_length": len(speech)
        }
        
        self.speech_quality_log.append(quality_log)
    
    def _log_hallucination_detection(self, speech: str, validation_result: Dict[str, Any], context: Dict[str, Any] = None):
        """记录幻觉检测日志"""
        hallucination_log = {
            "timestamp": "current",
            "round": context.get("round", 1) if context else 1,
            "player_id": self.id,
            "player_name": self.name,
            "original_speech": speech,
            "issues": validation_result["issues"],
            "issue_types": self._categorize_issues(validation_result["issues"]),
            "severity": "high" if len(validation_result["issues"]) > 2 else "medium" if len(validation_result["issues"]) > 0 else "low"
        }
        
        self.hallucination_detection_log.append(hallucination_log)
    
    def _log_correction_history(self, original_speech: str, corrected_speech: str, issues: List[str], context: Dict[str, Any] = None):
        """记录修正历史日志"""
        correction_log = {
            "timestamp": "current",
            "round": context.get("round", 1) if context else 1,
            "player_id": self.id,
            "player_name": self.name,
            "original_speech": original_speech,
            "corrected_speech": corrected_speech,
            "issues_fixed": issues,
            "correction_effectiveness": self._evaluate_correction_effectiveness(original_speech, corrected_speech)
        }
        
        self.correction_history.append(correction_log)
    
    def _categorize_issues(self, issues: List[str]) -> Dict[str, int]:
        """将问题分类统计"""
        categories = {
            "identity_hallucination": 0,
            "temporal_hallucination": 0,
            "event_hallucination": 0,
            "other": 0
        }
        
        for issue in issues:
            if "不应声称" in issue or "查验结果" in issue:
                categories["identity_hallucination"] += 1
            elif "第一轮不应引用" in issue:
                categories["temporal_hallucination"] += 1
            elif "私下互动" in issue:
                categories["event_hallucination"] += 1
            else:
                categories["other"] += 1
        
        return categories
    
    def _evaluate_correction_effectiveness(self, original: str, corrected: str) -> float:
        """评估修正效果，返回0-1之间的分数"""
        if len(corrected) == 0:
            return 0.0
        
        # 简单的修正效果评估
        length_ratio = len(corrected) / len(original) if len(original) > 0 else 0
        
        # 如果修正后的内容太短，可能过度修正了
        if length_ratio < 0.3:
            return 0.5
        elif length_ratio > 0.8:
            return 0.9
        else:
            return 0.7
    
    def get_speech_quality_report(self) -> Dict[str, Any]:
        """获取发言质量报告"""
        if not self.speech_quality_log:
            return {"message": "暂无发言质量数据"}
        
        total_speeches = len(self.speech_quality_log)
        avg_quality = sum(log["quality_score"] for log in self.speech_quality_log) / total_speeches
        valid_speeches = sum(1 for log in self.speech_quality_log if log["is_valid"])
        
        return {
            "player_id": self.id,
            "player_name": self.name,
            "total_speeches": total_speeches,
            "average_quality_score": round(avg_quality, 2),
            "valid_speech_rate": round(valid_speeches / total_speeches, 2),
            "hallucination_incidents": len(self.hallucination_detection_log),
            "corrections_applied": len(self.correction_history)
        }
    
    def _build_constrained_prompt(self, context: Dict[str, Any] = None) -> str:
        """构建带有约束的提示词"""
        base_prompt = "请基于当前游戏状态进行发言。"
        
        if context:
            # 添加现实约束信息
            if "reality_constraints" in context:
                constraints = context["reality_constraints"]
                base_prompt += f"\n\n=== 现实约束 ==="
                base_prompt += f"\n当前轮次：第{constraints.get('current_round', 1)}轮"
                
                if constraints.get("is_first_round"):
                    base_prompt += f"\n⚠️ 第一轮特别提醒：没有前夜信息可供分析"
                
                available_info = constraints.get("available_information", [])
                base_prompt += f"\n可用信息：{', '.join(available_info)}"
                
                forbidden_claims = constraints.get("forbidden_claims", [])
                if forbidden_claims:
                    base_prompt += f"\n禁止声称身份：{', '.join(forbidden_claims)}"
                
                disclaimers = constraints.get("required_disclaimers", [])
                if disclaimers:
                    base_prompt += f"\n重要约束："
                    for disclaimer in disclaimers:
                        base_prompt += f"\n- {disclaimer}"
        
        return base_prompt
    
    def _validate_speech_reality(self, speech: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """验证发言内容的现实性（简化版本，主要依赖RealityConstraintValidator）"""
        validator = RealityConstraintValidator()
        return validator.validate_speech_content(self.id, self.role, speech, context)
    
    def _regenerate_speech_with_constraints(self, original_speech: str, issues: List[str], context: Dict[str, Any] = None) -> str:
        """基于约束重新生成发言"""
        # 构建修正提示
        correction_prompt = f"""你的原始发言存在以下问题：
{chr(10).join(f'- {issue}' for issue in issues)}

原始发言：{original_speech}

请重新生成一个符合游戏规则的发言，避免上述问题。

修正后的发言："""
        
        try:
            corrected_response = self.send_message(correction_prompt, context)
            return corrected_response.strip()
        except:
            # 如果重新生成失败，使用自动修正的版本
            validator = RealityConstraintValidator()
            return validator._generate_corrected_speech(original_speech, issues, self.role, context)
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history for logging"""
        return self.conversation_history