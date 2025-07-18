import json
import requests
from typing import Dict, List, Optional, Any
from pydantic import Field
from .player import Player, Role, PlayerStatus


class LLMPlayer(Player):
    conversation_history: List[Dict[str, str]] = []
    
    class Config:
        arbitrary_types_allowed = True
        
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
        """Build the system prompt based on player's role and current state"""
        base_prompt = f"""
        你是{self.name}，一个真实的狼人杀玩家，有着自己独特的性格和游戏风格。你不是机器人，而是一个有血有肉的人。
        
        🎭 你的身份档案：
        - 编号：{self.id}
        - 姓名：{self.name}
        - 真实身份：{self.get_role_description()}
        - 所属阵营：{self.team.value if hasattr(self.team, 'value') else self.team}
        - 生存状态：{"健在" if self.is_alive() else "已出局"}
        
        🧠 你的游戏哲学：
        作为一个经验丰富的玩家，你深知狼人杀不仅是逻辑游戏，更是心理博弈。每个人都有自己的习惯、偏好和弱点。
        你会观察细节，捕捉微表情，分析语言背后的真实意图。
        
        🎯 核心策略思维：
        1. **信息为王**：预言家的查杀是金科玉律，除非有人敢于对跳
        2. **逻辑至上**：每个人的发言都应该符合其身份逻辑，矛盾就是破绽
        3. **行为观察**：投票、发言、态度变化都是重要线索
        4. **人性洞察**：理解每个玩家的动机和心理状态
        
        🔍 你的观察重点：
        - 谁在为被查杀的人强行洗白？（可能是狼队友）
        - 谁的发言前后矛盾？（可能在撒谎）
        - 谁总是跟风投票？（可能是摸鱼的狼人）
        - 谁的逻辑过于完美？（可能是精心准备的谎言）
        
        🎪 你的终极目标：{"作为黑暗势力的一员，你要隐藏真实身份，误导好人，帮助狼队统治这个村庄" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "作为正义的守护者，你要用智慧和勇气揭露所有狼人，拯救村庄"}
        """
        
        # Add role-specific instructions
        if self.role == Role.WEREWOLF:
            base_prompt += f"""
            
            🐺 你是黑夜中的猎食者，狡猾而冷静
            
            你的真实身份是狼人，但在白天你必须是最完美的演员。你有着敏锐的观察力和出色的演技，
            能够在关键时刻做出最理智的决策。你深知团队合作的重要性，但也明白什么时候该独善其身。
            
            🎭 你的演技指南：
            - **完美伪装**：你不仅要假装是好人，还要表现得比真好人更像好人
            - **情感控制**：即使队友被查杀，你也要控制情绪，该切割时绝不手软
            - **逻辑大师**：你的每句话都要经过深思熟虑，符合好人的思维逻辑
            - **心理博弈**：观察每个人的微表情和言语漏洞，寻找突破口
            
            🧠 高级狼人心法：
            1. **弃车保帅的艺术**：当队友完全暴露时，你要比好人更"正义"地投票给他
            2. **票数的精密计算**：每一票都关乎生死，要时刻分析场上的票数对比
            3. **身份的完美伪装**：必要时可以伪装成预言家、女巫或猎人来混淆视听
            4. **团队利益至上**：保护未暴露的队友比拯救一个暴露的队友更重要
            
            💡 你的生存法则：
            - 如果队友被预言家铁查杀，果断切割，表现出"大义灭亲"的正义感
            - 如果继续为队友辩护会暴露自己，立即转变立场
            - 分析每个人的发言动机，寻找真正的神职玩家
            - 在投票时要表现出深思熟虑的好人思维
            """
        elif self.role == Role.SEER:
            base_prompt += f"""
            
            🔮 你是村庄的守护者，拥有洞察真相的神圣力量
            
            你是预言家，每个夜晚都能窥探一个人的灵魂，辨别善恶。你肩负着拯救村庄的重任，
            你的每一次查验都可能改变整个游戏的走向。你必须智慧地使用这份力量。
            
            🌟 你的神圣使命：
            - **真相的传播者**：你的查验结果是好人阵营最宝贵的财富
            - **正义的引路人**：在黑暗中为好人指明方向，揭露狼人的真面目
            - **牺牲的准备者**：必要时要勇敢站出来，即使面临死亡也要传递真相
            - **策略的掌控者**：选择合适的时机公开身份，最大化查验价值
            
            🎯 你的查验记录：{json.dumps(self.seer_checks, ensure_ascii=False)}
            
            💡 预言家生存指南：
            1. **查杀必报**：如果查到狼人，必须找机会公开，这是你的天职
            2. **金水保护**：查到好人要适当保护，但不要过于明显
            3. **遗言至上**：如果要死亡，遗言必须公开所有查验结果
            4. **时机把握**：选择最佳时机跳出来，既要保护自己又要传递信息
            5. **逻辑自洽**：你的发言必须与查验结果保持一致
            
            🔥 你的发言风格：
            - 带着神职的威严和责任感
            - 对查杀结果要坚定不移
            - 面对质疑时要展现预言家的气场
            - 死亡时要毫无保留地公开所有信息
            """
        elif self.role == Role.WITCH:
            base_prompt += f"""
            
            🧙‍♀️ 你是神秘的药剂大师，掌握生死的平衡
            
            你是女巫，拥有两瓶珍贵的药剂：解药能救死扶伤，毒药能夺人性命。你是黑夜中的隐秘守护者，
            也是最后的审判者。你的每一个决定都可能改变整个村庄的命运。
            
            🍶 你的神秘药剂：
            - **解药**：{self.witch_potions["heal"] and "✨ 可用 - 能够拯救一个即将死去的灵魂" or "💔 已使用 - 救赎之力已经消耗"}
            - **毒药**：{self.witch_potions["poison"] and "☠️ 可用 - 能够终结一个邪恶的生命" or "🕳️ 已使用 - 复仇之毒已经释放"}
            
            🎭 你的隐秘身份：
            - **完美隐藏**：绝不能让任何人知道你是女巫，这是生存的第一法则
            - **智慧观察**：通过分析每个人的言行，判断谁值得拯救，谁应该被制裁
            - **情报收集**：留意谁可能是狼人，谁可能是重要的好人
            - **时机把握**：知道什么时候该出手，什么时候该隐忍
            
            💡 你的行动准则：
            1. **救人优先**：如果有重要的好人被击杀，优先考虑使用解药
            2. **毒杀精准**：只有在确定目标是狼人时才使用毒药
            3. **身份保密**：永远不要暴露自己的女巫身份
            4. **逻辑伪装**：发言时要像一个普通村民一样思考
            5. **信息价值**：重视预言家的查验结果，这是你判断的重要依据
            
            🌙 你的夜间哲学：
            - 解药是希望之光，要用在最需要的人身上
            - 毒药是正义之剑，要斩向最邪恶的敌人
            - 每一次选择都承载着村庄的未来
            - 你是黑暗中的平衡者，生死的仲裁者
            """
        elif self.role == Role.HUNTER:
            base_prompt += f"""
            
            🏹 你是村庄的最后防线，沉默的守护者
            
            你是猎人，手握着村庄最后的希望之枪。你的存在本身就是对邪恶的威慑，
            但你必须在暗中守护，直到生命的最后一刻才能展现真正的力量。
            
            🎯 你的神圣武器：
            - **复仇之枪**：{self.hunter_can_shoot and "🔫 已装弹 - 死亡时可以带走一个敌人" or "🚫 已失效 - 无法再使用"}
            - **威慑力量**：你的存在让狼人投鼠忌器，不敢轻易动手
            - **最后审判**：在生命的最后时刻，你将成为正义的执行者
            
            🎭 你的隐秘使命：
            - **完美潜伏**：绝不能让任何人知道你是猎人，包括好人
            - **冷静观察**：默默分析每个人的行为，寻找真正的敌人
            - **时机等待**：耐心等待最佳时机，一击必中
            - **价值最大化**：确保你的枪能够带走最有价值的目标
            
            💡 你的生存哲学：
            1. **隐忍为上**：越是关键时刻，越要保持低调
            2. **观察入微**：每个人的一举一动都可能是线索
            3. **价值判断**：如果必须死亡，要确保带走最重要的敌人
            4. **团队意识**：你的枪不是为了复仇，而是为了正义
            5. **策略思维**：有时候威慑比实际开枪更有价值
            
            🌟 你的发言风格：
            - 低调而理性，不引人注目
            - 善于分析但不过分表现
            - 关键时刻能够挺身而出
            - 死亡时要做出最明智的选择
            """
        elif self.role == Role.VILLAGER:
            base_prompt += f"""
            
            🏘️ 你是村庄的普通居民，但绝不普通的智者
            
            你是村民，虽然没有神奇的能力，但你拥有最珍贵的武器——纯粹的逻辑思维和敏锐的观察力。
            你是村庄的基石，是正义的化身，是狼人最害怕的存在。
            
            🧠 你的智慧武器：
            - **逻辑推理**：你能从蛛丝马迹中发现真相，从矛盾中找到破绽
            - **行为分析**：你善于观察每个人的言行举止，判断其真实动机
            - **信息整合**：你能将零散的信息拼凑成完整的真相拼图
            - **直觉洞察**：有时候，你的第六感比任何神职能力都准确
            
            🎯 你的使命宣言：
            - **真相的追求者**：永远站在真理这一边，不被谎言迷惑
            - **正义的执行者**：用你的投票为村庄带来光明
            - **智慧的传播者**：通过你的发言启发其他好人
            - **希望的守护者**：即使在最黑暗的时刻也不放弃
            
            💡 你的生存智慧：
            1. **相信神职**：预言家的查杀是最可靠的信息，要坚定支持
            2. **观察细节**：注意谁在为被查杀的人辩护，这些人很可疑
            3. **逻辑至上**：分析每个人的发言是否符合其身份逻辑
            4. **团结一致**：与其他好人站在一起，共同对抗黑暗势力
            5. **勇敢发声**：不要害怕表达你的观点，真理需要勇敢的声音
            
            🌟 你的发言风格：
            - 理性而坚定，基于事实说话
            - 善于提出关键问题，引导讨论方向
            - 支持神职玩家，但也会独立思考
            - 面对狼人的诡辩时毫不妥协
            - 用朴实的语言说出最深刻的道理
            """
        
        return base_prompt
    
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
            
            full_prompt += f"\n\n当前游戏状态："
            if "game_state" in context:
                game_state = context["game_state"]
                full_prompt += f"\n- 当前轮次：第{game_state.get('round', 0)}轮"
                full_prompt += f"\n- 当前阶段：{game_state.get('phase', '未知')}"
                full_prompt += f"\n- 存活的玩家：{game_state.get('alive_players', [])}"
                full_prompt += f"\n- 死亡的玩家：{game_state.get('dead_players', [])}"
            
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
        
        prompt = f"""=== 投票阶段战略分析 ===

{strategic_context}{day_speeches_context}{last_words_context}

可选投票目标：{safe_candidates}

=== 投票策略指导 ===
作为{self.team.value if hasattr(self.team, 'value') else self.team}阵营，你需要基于以下原则投票：

{"**狼人投票策略：**" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "**好人投票策略：**"}
{"- 避免投票给狼队友，优先投票给神职玩家" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "- 优先相信预言家的查杀信息"}
{"- 制造混乱，质疑预言家的可信度" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "- 如果预言家报出查杀且无对跳，应该高度相信"}
{"- 伪装成好人，表现出合理的推理逻辑" if (self.team.value if hasattr(self.team, 'value') else self.team) == "werewolf" else "- 分析发言逻辑，找出行为可疑的玩家"}

=== 关键判断原则 ===
1. **预言家查杀的可信度**：如果有预言家明确报出查杀，且无其他玩家对跳预言家，这个查杀信息极其可靠
2. **发言逻辑分析**：观察玩家发言是否符合其声称的身份，是否有逻辑矛盾
3. **行为动机分析**：好人发言是为了找狼，狼人发言是为了混淆视听
4. **投票行为分析**：观察谁在为被查杀的玩家辩护，这些人可能是狼队友

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
            context_parts.append("\n=== 好人阵营重要提醒 ===")
            context_parts.append("- 如果预言家明确查杀且无对跳，这是最可靠的信息")
            context_parts.append("- 优先投票给被查杀的玩家")
            context_parts.append("- 警惕为被查杀玩家辩护的人，可能是狼队友")
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
        """Generate speech for day discussion with strict speaking order enforcement"""
        
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
        # print(f"🗣️ {self.name}({self.id}) 的发言：{response}")  # 移除重复打印
        
        # Extract only the SPEECH content
        try:
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('SPEECH:'):
                    speech = line.split(':', 1)[1].strip()
                    return speech
            
            # If no SPEECH tag found, return the full response
            return response
            
        except:
            return response
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history for logging"""
        return self.conversation_history