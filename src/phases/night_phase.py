from typing import List, Dict, Any, Optional
from ..models.player import Role, PlayerStatus
from ..game.game_state import GameState


class NightPhase:
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.night_events = []
        
    def execute_night_phase(self) -> Dict[str, Any]:
        """Execute the complete night phase with all roles"""
        print(f"=== 第{self.game_state.current_round}轮夜晚开始 ===")
        
        self.night_events.clear()
        
        # Clear previous night actions
        self.game_state.night_actions.clear()
        self.game_state.wolf_kill_target = None
        self.game_state.seer_check_result = None
        self.game_state.witch_heal_used = False
        self.game_state.witch_poison_used = False
        self.game_state.hunter_shot = None
        self.game_state.deaths_this_night.clear()
        
        # 1. Seer action
        seer_result = self._seer_phase()
        if seer_result:
            self.night_events.append(seer_result)
        
        # 2. Werewolf action
        wolf_result = self._werewolf_phase()
        if wolf_result:
            self.night_events.append(wolf_result)
            self.game_state.wolf_kill_target = wolf_result.get("target")
        
        # 3. Witch action
        witch_result = self._witch_phase()
        if witch_result:
            self.night_events.append(witch_result)
            # Debug: Print current state after witch action
            # print(f"🔍 DEBUG: After witch action - witch_heal_used: {self.game_state.witch_heal_used}")
            # print(f"🔍 DEBUG: wolf_kill_target: {self.game_state.wolf_kill_target}")
        
        # 4. Hunter check (if killed)
        hunter_result = self._hunter_phase()
        if hunter_result:
            self.night_events.append(hunter_result)
        
        # 5. Process all night actions and determine deaths
        deaths = self._process_night_actions()
        
        # Update game state
        for death in deaths:
            self.game_state.kill_player(death)
            self.game_state.deaths_this_night.append(death)
        
        # Print detailed night summary
        print(f"\n=== 📊 第{self.game_state.current_round}轮夜晚行动总结 ===")
        for event in self.night_events:
            if event["type"] == "seer_check":
                player = self.game_state.get_player_by_id(event["player"])
                target = self.game_state.get_player_by_id(event["target"])
                print(f"🔮 预言家 {player.name}({player.id}) 查验 {target.name}({target.id}) 结果为：{event['result']}")
            elif event["type"] == "wolf_kill":
                target = self.game_state.get_player_by_id(event["target"])
                wolves = [self.game_state.get_player_by_id(w_id) for w_id in event["voters"]]
                wolf_names = ", ".join([f"{w.name}({w.id})" for w in wolves])
                print(f"🐺 狼人团队({wolf_names}) 决定击杀 {target.name}({target.id})")
            elif event["type"] == "witch_heal":
                player = self.game_state.get_player_by_id(event["player"])
                target = self.game_state.get_player_by_id(event["target"])
                print(f"🧙‍♀️ 女巫 {player.name}({player.id}) 使用解药救了 {target.name}({target.id})")
            elif event["type"] == "witch_poison":
                player = self.game_state.get_player_by_id(event["player"])
                target = self.game_state.get_player_by_id(event["target"])
                print(f"🧙‍♀️☠️ 女巫 {player.name}({player.id}) 使用毒药毒死了 {target.name}({target.id})")
            elif event["type"] == "witch_no_action":
                player = self.game_state.get_player_by_id(event["player"])
                print(f"🧙‍♀️⏭️ 女巫 {player.name}({player.id}) 选择不使用药物")
        
        if deaths:
            dead_players = [self.game_state.get_player_by_id(d) for d in deaths]
            dead_names = ", ".join([f"{p.name}({p.id})" for p in dead_players])
            print(f"💀 夜晚死亡玩家：{dead_names}")
        else:
            print("🌙 平安夜，无人死亡")
        
        print("=" * 50)
        
        return {
            "round": self.game_state.current_round,
            "deaths": deaths,
            "events": self.night_events,
            "wolf_kill_target": self.game_state.wolf_kill_target,
            "witch_heal_used": self.game_state.witch_heal_used,
            "witch_poison_used": self.game_state.witch_poison_used
        }
    
    def _seer_phase(self) -> Optional[Dict[str, Any]]:
        """Handle seer's night action"""
        seers = self.game_state.get_alive_players_by_role(Role.SEER)
        if not seers:
            return None
        
        seer = seers[0]  # Only one seer
        if not seer.is_alive():
            return None
        
        print(f"🔮 预言家 {seer.name}({seer.id}) 开始行动...")
        
        # Get context for seer with specific seer context
        context = self.game_state.get_context_for_player(seer.id, "seer")
        
        # Show available targets
        alive_players = [p.id for p in self.game_state.get_alive_players() if p.id != seer.id]
        unchecked_players = [p for p in alive_players if p not in seer.seer_checks]
        
        if not unchecked_players:
            print(f"🔄 预言家 {seer.name}({seer.id}) 已查验所有玩家")
            return None
        
        # Build context for LLM - use the new seer context format
        context_data = self.game_state.get_context_for_player(seer.id, "seer")
        
        # Add additional game state data needed by make_night_action
        context_data.update({
            "game_state": {
                "round": self.game_state.current_round,
                "phase": "night",
                "alive_players": [p.id for p in self.game_state.get_alive_players()],
                "players": {p.id: {"name": p.name, "role": p.role.value} for p in self.game_state.players}
            }
        })
        
        # Get seer's action
        action = seer.make_night_action(context_data)
        
        if action and action.get("action") == "check":
            target_id = action.get("target")
            target_player = self.game_state.get_player_by_id(target_id)
            
            if target_player:
                result = "狼人" if target_player.role == Role.WEREWOLF else "好人"
                seer.seer_checks[target_id] = result
                
                print(f"🔮 预言家 {seer.name}({seer.id}) 查验了 {target_player.name}({target_id})，结果是：{result}")
                
                return {
                    "type": "seer_check",
                    "player": seer.id,
                    "target": target_id,
                    "result": result,
                    "action": "check"
                }
        
        return None
    
    def _werewolf_phase(self) -> Optional[Dict[str, Any]]:
        """Handle werewolf night action"""
        wolves = self.game_state.get_alive_wolf_players()
        if not wolves:
            return None
        
        wolf_names = [w.name for w in wolves]
        print(f"🐺 狼人开始行动... ({', '.join(wolf_names)})")
        
        # Get wolf team context using specific wolf context
        wolf_ids = [w.id for w in wolves]
        context_data = self.game_state.get_context_for_player(wolves[0].id, "wolf")
        
        # Add additional game state data needed by make_night_action
        context_data.update({
            "game_state": {
                "round": self.game_state.current_round,
                "phase": "night",
                "alive_players": [p.id for p in self.game_state.get_alive_players()],
                "players": {p.id: {"name": p.name, "role": p.role.value} for p in self.game_state.players}
            },
            "wolf_team": wolf_ids
        })
        
        # 获取狼人编号（2,5,7）和其他可用目标
        wolf_ids = [w.id for w in wolves]
        available_targets = [p for p in self.game_state.get_alive_players() if p.id not in wolf_ids]
        
        target_display = [f"{p.name}({p.id})" for p in available_targets]
        print(f"🐺 狼人团队({', '.join([f'{w.name}({w.id})' for w in wolves])})开始投票...")
        print(f"可选击杀目标：{', '.join(target_display)}")
        
        # 狼人团队投票选择击杀目标
        wolf_votes = {}
        for wolf in wolves:
            if wolf.is_alive():
                action = wolf.make_night_action(context_data)
                if action and action.get("action") == "kill":
                    target = action.get("target")
                    if target in [p.id for p in available_targets]:
                        wolf_votes[wolf.id] = target
                        target_player = self.game_state.get_player_by_id(target)
                        print(f"🐺 狼人 {wolf.name}({wolf.id}) 投票击杀 {target_player.name}({target})")
        
        # 基于狼人团队的投票结果做决定
        if wolf_votes:
            # 统计狼人投票
            vote_count = {}
            for wolf_id, target in wolf_votes.items():
                vote_count[target] = vote_count.get(target, 0) + 1
            
            # 找出得票最多的目标
            max_votes = max(vote_count.values())
            most_voted = [t for t, v in vote_count.items() if v == max_votes]
            
            # 平票时从平票结果中随机选择
            import random
            final_target = random.choice(most_voted)
            target_player = self.game_state.get_player_by_id(final_target)
            
            print(f"🐺🎯 狼人团队投票结果：{dict(vote_count)}")
            print(f"🐺🎯 最终击杀目标：{target_player.name}({final_target})")
            return {
                "type": "wolf_kill",
                "target": final_target,
                "voters": list(wolf_votes.keys()),
                "action": "kill"
            }
        
        # 狼人团队无法投票时的回退
        non_wolf_players = [p.id for p in self.game_state.get_alive_players() if p not in wolves]
        if non_wolf_players:
            import random
            final_target = random.choice(non_wolf_players)
            target_player = self.game_state.get_player_by_id(final_target)
            print(f"🐺⚠️ 狼人团队无法投票，随机选择击杀 {target_player.name}({final_target})")
            return {
                "type": "wolf_kill",
                "target": final_target,
                "voters": [w.id for w in wolves],
                "action": "kill"
            }
        
        return None
    
    def _witch_phase(self) -> Optional[Dict[str, Any]]:
        """Handle witch's night action"""
        witches = self.game_state.get_alive_players_by_role(Role.WITCH)
        if not witches:
            return None
        
        witch = witches[0]  # Only one witch
        if not witch.is_alive():
            return None
        
        print(f"🧙‍♀️ 女巫 {witch.name}({witch.id}) 开始行动...")
        
        # Prepare context for witch with specific witch context
        context_data = self.game_state.get_context_for_player(witch.id, "witch")
        # 确保女巫知道被狼人击杀的玩家
        context_data["killed_player"] = self.game_state.wolf_kill_target
        
        # Add additional game state data needed by make_night_action
        context_data.update({
            "game_state": {
                "round": self.game_state.current_round,
                "phase": "night",
                "alive_players": [p.id for p in self.game_state.get_alive_players()],
                "players": {p.id: {"name": p.name, "role": p.role.value} for p in self.game_state.players}
            }
        })
        
        # Get witch's action
        action = witch.make_night_action(context_data)
        
        if action and action.get("action") == "heal":
            target = action.get("target")
            
            # 确保类型一致性和有效性检查
            try:
                target_int = int(target) if target is not None else None
                wolf_target_int = int(self.game_state.wolf_kill_target) if self.game_state.wolf_kill_target is not None else None
                
                # 验证女巫是否可以使用解药
                if (target_int is not None and 
                    wolf_target_int is not None and 
                    target_int == wolf_target_int and 
                    witch.witch_potions["heal"]):
                    
                    # 立即更新状态，确保同步
                    witch.witch_potions["heal"] = False
                    self.game_state.witch_heal_used = True
                    
                    print(f"🧙‍♀️ 女巫 {witch.name}({witch.id}) 使用解药救了 {target_int}")
                    print(f"🔍 DEBUG: 女巫解药状态已更新 - witch_heal_used: {self.game_state.witch_heal_used}")
                    
                    return {
                        "type": "witch_heal",
                        "target": target_int,
                        "player": witch.id,
                        "action": "heal"
                    }
                else:
                    print(f"🔍 DEBUG: 女巫解药使用失败 - target: {target_int}, wolf_target: {wolf_target_int}, potion_available: {witch.witch_potions['heal']}")
                    
            except (ValueError, TypeError) as e:
                print(f"🔍 DEBUG: 女巫解药类型转换错误: {e}")
        
        elif action and action.get("action") == "poison":
            target = action.get("target")
            target_player = self.game_state.get_player_by_id(target)
            
            if target_player and target_player.is_alive() and witch.witch_potions["poison"]:
                witch.witch_potions["poison"] = False
                self.game_state.witch_poison_used = True
                
                print(f"🧙‍♀️☠️ 女巫 {witch.name}({witch.id}) 使用毒药毒死了 {target_player.name}({target})")
                
                return {
                    "type": "witch_poison",
                    "target": target,
                    "player": witch.id,
                    "action": "poison"
                }
        
        elif action and action.get("action") == "none":
            print(f"🧙‍♀️⏭️ 女巫 {witch.name}({witch.id}) 选择不使用任何药物")
            return {
                "type": "witch_no_action",
                "player": witch.id,
                "action": "none"
            }
        
        return None
    
    def _hunter_phase(self) -> Optional[Dict[str, Any]]:
        """Handle hunter's night action (if killed)"""
        hunters = self.game_state.get_alive_players_by_role(Role.HUNTER)
        if not hunters:
            return None
        
        hunter = hunters[0]  # Only one hunter
        
        # Check if hunter was killed this night
        potential_deaths = []
        
        # Check wolf kill
        if self.game_state.wolf_kill_target and not self.game_state.witch_heal_used:
            if self.game_state.wolf_kill_target == hunter.id:
                potential_deaths.append(hunter.id)
        
        # Check witch poison
        if hasattr(self, '_witch_poison_target') and self._witch_poison_target == hunter.id:
            potential_deaths.append(hunter.id)
        
        if hunter.id in potential_deaths and hunter.hunter_can_shoot:
            print(f"猎人 {hunter.name} 被击杀，可以选择开枪...")
            
            context = self.game_state.get_context_for_player(hunter.id)
            context["death_reason"] = "被狼人击杀"
            
            # For now, hunter doesn't shoot at night (only during day)
            # This can be extended later
            return {
                "type": "hunter_death",
                "player": hunter.id,
                "shot": None  # Hunter can shoot during day phase
            }
        
        return None
    
    def _process_night_actions(self) -> List[int]:
        """Process all night actions and determine who dies"""
        deaths = []
        
        # Debug: Print current state for troubleshooting
        print(f"🔍 DEBUG: 处理夜晚行动 - wolf_kill_target = {self.game_state.wolf_kill_target}")
        print(f"🔍 DEBUG: 处理夜晚行动 - witch_heal_used = {self.game_state.witch_heal_used}")
        
        # Wolf kill (unless healed by witch)
        if self.game_state.wolf_kill_target:
            if not self.game_state.witch_heal_used:
                target_player = self.game_state.get_player_by_id(self.game_state.wolf_kill_target)
                if target_player and target_player.is_alive():
                    deaths.append(self.game_state.wolf_kill_target)
                    print(f"🔍 DEBUG: 狼人击杀生效 - 添加 {self.game_state.wolf_kill_target} 到死亡列表")
            else:
                target_player = self.game_state.get_player_by_id(self.game_state.wolf_kill_target)
                if target_player:
                    print(f"🔍 DEBUG: 狼人击杀被女巫解药阻止 - {target_player.name}({self.game_state.wolf_kill_target}) 被救")
        
        # Witch poison
        for event in self.night_events:
            if event["type"] == "witch_poison":
                target = event["target"]
                target_player = self.game_state.get_player_by_id(target)
                if target_player and target_player.is_alive():
                    deaths.append(target)
                    print(f"🔍 DEBUG: 女巫毒药生效 - 添加 {target} 到死亡列表")
        
        # Remove duplicates and sort
        deaths = list(set(deaths))
        deaths.sort()
        
        print(f"🔍 DEBUG: 最终夜晚死亡列表: {deaths}")
        
        return deaths