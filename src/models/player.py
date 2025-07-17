from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class Role(Enum):
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    VILLAGER = "villager"


class Team(Enum):
    WEREWOLF = "werewolf"
    VILLAGER = "villager"


class PlayerStatus(Enum):
    ALIVE = "alive"
    DEAD = "dead"


class Player(BaseModel):
    id: int
    name: str
    role: Role
    team: Team = None  # Make team optional, will be set automatically
    status: PlayerStatus = PlayerStatus.ALIVE
    api_url: str
    api_key: str
    model: str = "gpt-3.5-turbo"
    
    # Role-specific state
    seer_checks: Dict[int, str] = {}  # player_id -> "good"/"werewolf"
    witch_potions: Dict[str, bool] = {"heal": True, "poison": True}
    hunter_can_shoot: bool = True
    
    class Config:
        arbitrary_types_allowed = True
        use_enum_values = True
    
    def __init__(self, **data):
        super().__init__(**data)
        # Ensure role is properly converted to Role enum
        if isinstance(self.role, str):
            self.role = Role(self.role)
        
        # Automatically set team based on role if not provided
        if self.team is None:
            if self.role == Role.WEREWOLF:
                self.team = Team.WEREWOLF
            else:
                self.team = Team.VILLAGER
    
    def is_alive(self) -> bool:
        return self.status == PlayerStatus.ALIVE
    
    def kill(self):
        self.status = PlayerStatus.DEAD
    
    def get_role_description(self) -> str:
        role_desc = {
            Role.WEREWOLF: "狼人 - 每晚可以杀人",
            Role.SEER: "预言家 - 每晚可以查验一名玩家身份",
            Role.WITCH: "女巫 - 有解药和毒药各一瓶",
            Role.HUNTER: "猎人 - 死亡时可以开枪带走一名玩家",
            Role.VILLAGER: "村民 - 无特殊技能，通过推理找出狼人"
        }
        return role_desc[self.role]