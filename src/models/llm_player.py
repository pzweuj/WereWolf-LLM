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
                "temperature": 0.7,
                "max_tokens": 8192,
                "max_length": 4000
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
        你是一名经验丰富的狼人杀玩家，具备良好的逻辑推理能力和游戏策略意识。
        
        你的身份信息：
        - 编号：{self.id}
        - 名字：{self.name}
        - 身份：{self.get_role_description()}
        - 阵营：{self.team.value}
        - 状态：{"存活" if self.is_alive() else "已死亡"}
        
        核心游戏策略原则：
        1. 信息价值：预言家的查杀信息是最可靠的，除非有明确的对跳情况
        2. 逻辑一致性：分析玩家发言的逻辑是否自洽，是否符合其声称的身份
        3. 行为分析：观察玩家的投票行为、发言态度是否符合好人思维
        4. 阵营判断：优先相信已验证的神职玩家，警惕可疑行为
        
        关键判断标准：
        - 如果有预言家报出查杀且无人对跳，应该高度相信查杀结果
        - 如果有多人跳预言家，需要通过逻辑和行为判断真假
        - 注意观察谁在为被查杀的玩家辩护，这些人可能是狼队友
        - 分析发言的动机：好人发言是为了找狼，狼人发言是为了混淆视听
        
        你的目标：{"帮助狼队获胜，隐藏身份并误导好人" if self.team.value == "werewolf" else "通过逻辑推理找出所有狼人"}
        """
        
        # Add role-specific instructions
        if self.role == Role.WEREWOLF:
            base_prompt += f"""
            作为狼人，你可以和同伴交流，每晚要选择一名玩家击杀。
            注意隐藏身份，在白天发言时要假装是好人。
            
            狼人高级策略：
            1. **队友保护策略**：适度为队友辩护，但不能过于明显
            2. **弃车保帅策略**：当队友完全暴露且无法挽救时，果断切割保护自己
            3. **票数分析**：时刻分析场上票数对比，评估是否需要牺牲队友
            4. **身份伪装**：始终表现出好人思维，避免暴露狼人身份
            
            关键判断标准：
            - 如果队友被预言家查杀且无法反驳，考虑是否需要切割
            - 如果继续为队友辩护会暴露自己，果断放弃队友
            - 如果狼队票数明显不足以救队友，选择保护自己和其他队友
            - 分析场上局势，优先保证狼队整体利益
            
            发言时特别注意：
            - 只能分析已发言玩家的内容
            - 不能假设未发言玩家的身份或行为
            - 避免狼人团队内部的明显暗示
            - 必要时可以投票给暴露的队友以保护自己
            """
        elif self.role == Role.SEER:
            base_prompt += f"""
            作为预言家，你每晚可以查验一名玩家的身份。
            查验结果会显示为"好人"或"狼人"。
            你的查验记录：{json.dumps(self.seer_checks, ensure_ascii=False)}
            
            关键策略：
            1. 如果查验到狼人，必须在合适的时机公开，尤其是死亡时
            2. 如果是好人，可以暗示或明确说明以帮助好人阵营
            3. 死亡时必须立即公开所有查验结果（遗言阶段）
            4. 不要为了隐藏身份而牺牲好人阵营的胜利
            
            发言时特别注意：
            - 如果死亡，必须立即公开查验结果
            - 可以基于查验结果做明确分析
            - 避免无谓的隐藏，预言家的价值在于提供信息
            """
        elif self.role == Role.WITCH:
            base_prompt += f"""
            作为女巫，你有：
            解药：{self.witch_potions["heal"] and "可用" or "已使用"}
            毒药：{self.witch_potions["poison"] and "可用" or "已使用"}
            每晚你可以选择使用解药救人或使用毒药杀人，但不能同时使用。
            
            发言时特别注意：
            - 不能暴露自己女巫的身份
            - 只能基于已发言玩家的内容做分析
            - 避免提及未发言玩家的救药或毒杀可能性
            """
        elif self.role == Role.HUNTER:
            base_prompt += f"""
            作为猎人，你死亡时可以选择开枪带走一名玩家。
            被毒杀或自刀时不能开枪。
            你现在可以开枪：{self.hunter_can_shoot and "是" or "否"}
            
            发言时特别注意：
            - 不能暴露自己猎人的身份
            - 只能基于已发言玩家的内容做分析
            - 避免提及未发言玩家的开枪目标
            """
        elif self.role == Role.VILLAGER:
            base_prompt += f"""
            作为村民，你无特殊技能，通过推理找出狼人。
            
            发言时特别注意：
            - 只能基于已发言玩家的内容做分析
            - 不能假设未发言玩家的身份或行为
            - 专注于逻辑推理而非主观猜测
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
    
    def vote_for_player(self, candidates: List[int], reason: str = None) -> int:
        """Ask the LLM to vote for a player with strategic analysis"""
        # Remove self from candidates if present
        safe_candidates = [c for c in candidates if c != self.id]
        if not safe_candidates:
            return candidates[0] if candidates else self.id
        
        # Build strategic voting context
        strategic_context = self._build_voting_context()
        
        prompt = f"""=== 投票阶段战略分析 ===

{strategic_context}

可选投票目标：{safe_candidates}

=== 投票策略指导 ===
作为{self.team.value}阵营，你需要基于以下原则投票：

{"**狼人投票策略：**" if self.team.value == "werewolf" else "**好人投票策略：**"}
{"- 避免投票给狼队友，优先投票给神职玩家" if self.team.value == "werewolf" else "- 优先相信预言家的查杀信息"}
{"- 制造混乱，质疑预言家的可信度" if self.team.value == "werewolf" else "- 如果预言家报出查杀且无对跳，应该高度相信"}
{"- 伪装成好人，表现出合理的推理逻辑" if self.team.value == "werewolf" else "- 分析发言逻辑，找出行为可疑的玩家"}

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
        print(f"投票阶段 - {self.name}({self.id}) 的投票决策：{response}")
        
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
        
        if self.team.value == "villager":
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

可选击杀目标（都是村民身份）：
"""
        for pid in non_wolf_players:
            name = target_names.get(pid, f"玩家{pid}")
            prompt += f"- {name}({pid})\n"
        
        prompt += f"""
作为狼人团队，你们需要统一选择一个目标进行击杀。

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
        print(f"🧙‍♀️ 女巫 {self.name}({self.id}) 的私人决策：{response}")
        
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
        
        # Role-specific speech constraints
        role_constraints = ""
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
- 可以基于场面情况透露自己是猎人
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
2. 公开所有查验结果（玩家ID和对应身份）
3. 给出下一步好人阵营的建议

示例遗言：
LAST_WORDS: 我是预言家，我查验了玩家3是狼人，玩家5是好人。根据查验结果，玩家3肯定是狼人，建议好人优先投票淘汰他。

请发表你的遗言："""
        else:
            prompt = f"""请发表你的看法和推理。严格遵守以下规则和格式：

=== 当前发言环境 ===
- 你是第{my_position}个发言的玩家
{chr(10).join(f'- {item}' for item in speech_context)}

=== 身份限制 ==={role_constraints}

=== 发言格式要求 ===
请严格按照以下格式回复：

SPEECH: [你的发言内容]

发言内容要求：
1. **必须明确提及你是第几个发言**（例如："我是第{my_position}个发言"）
2. **必须基于已发言玩家的内容**做分析
3. **不能提及未发言玩家的任何信息**
4. **不要分点描述，使用一句400字以内的话完成自己的发言**
5. **使用逻辑推理而非主观猜测**
6. **避免绝对判断，使用"可能"、"倾向于"等表述"

示例发言：
SPEECH: 我是第{my_position}个发言。根据前面张三的发言，我认为他的逻辑有些问题。他说自己是村民，但是对狼人行为的分析过于详细，这让我有些怀疑。不过这只是初步判断，还需要更多信息。

请开始你的发言："""
        
        response = self.send_message(prompt, context)
        print(f"🗣️ {self.name}({self.id}) 的发言：{response}")
        
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