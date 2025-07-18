# 🐺 LLM狼人杀游戏

一个由10个LLM玩家参与的狼人杀游戏实现，支持完整的游戏规则和MVP评选。

游戏多轮次发展，累积上下文会越来越多，因此建议使用上下文支持多的模型。

## 🎮 项目特色

- **完全自动化**: 10个LLM玩家自主进行游戏
- **完整规则**: 遵循标准狼人杀游戏规则
- **实时日志**: 详细记录所有对话和游戏事件
- **MVP评选**: 游戏结束后所有玩家投票选出MVP
- **灵活配置**: 支持不同LLM模型和API提供商

## 📋 游戏规则

### 角色配置
- **狼人阵营 (3人)**: 每晚集体杀人，目标淘汰所有神职和村民
- **预言家 (1人)**: 查验玩家身份为"好人"或"狼人"  
- **女巫 (1人)**: 拥有解药和毒药各1次，不可同晚使用
- **猎人 (1人)**: 死亡后可开枪带走一名玩家
- **村民 (4人)**: 无特殊技能，通过逻辑推理找出狼人

### 游戏流程

#### 🌙 夜晚行动顺序
1. **预言家行动**: 选择查验一名玩家身份
2. **狼人行动**: 集体选择击杀目标（可自刀，不可自爆）
3. **女巫行动**: 得知被击杀玩家，可选择使用解药或毒药
4. **猎人行动**: 若被击杀，可选择是否开枪带走一名玩家

#### ☀️ 白天阶段规则
1. **死亡公告**: 宣布昨夜死亡情况
2. **遗言规则**: 
   - 首夜死亡：所有死亡玩家均有遗言
   - 后续夜晚：仅1人死亡有遗言，多人死亡无遗言
3. **发言讨论**: 存活玩家轮流发言推理
4. **投票淘汰**: 投票处决一名嫌疑人
5. **猎人开枪**: 若猎人被投票淘汰，可选择开枪

### 胜利条件
- **狼人胜利**: 所有神职和村民被淘汰，或狼人人数等于好人人数
- **好人胜利**: 所有狼人被淘汰

#### 🏆 特殊规则
- 女巫药物用完后，若场面上1:1则狼人直接胜利
- 狼人不可自刀
- 猎人被毒杀或自刀时不能开枪
- 所有玩家可在发言时伪装身份进行欺骗

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置游戏
```bash
# 使用示例配置
python config/validate_config.py game_config.json

# 或使用自定义配置
python config/validate_config.py my_config.json

# 对自定义配置重新随机分配编号和角色
python config/reshuffle_config.py my_config.json
```

### 3. 运行游戏
```bash
python main.py my_config.json
```

## ⚙️ 配置文件

### 基本格式
```
config/game_config_template.json
```

### 角色配置要求
- 狼人: 3个
- 预言家: 1个 
- 女巫: 1个
- 猎人: 1个
- 村民: 4个

### 支持的模型
- OpenAI兼容API

## 📊 日志系统

所有游戏数据自动保存到 `logs/` 目录：

- `game_{id}.jsonl` - 游戏事件记录
- `conversations_{id}.jsonl` - 玩家对话记录 
- `summary_{id}.json` - 游戏总结和MVP结果

## 🔧 开发工具

### 配置验证
```bash
python config/validate_config.py game_config.json
```

### 设置测试
```bash
python test_setup.py
```

## 📁 项目结构

```
├── main.py                   # 主程序入口
├── requirements.txt          # 依赖列表
├── config/
│   ├── game_config_template.json
│   ├── reshuffle_config.py   # 对配置文件重新随机分配编号和角色
│   └── validate_config.py    # 配置验证工具
├── logs/                     # 游戏日志（自动生成）
└── src/
    ├── models/
    │   ├── player.py         # 基础玩家模型
    │   └── llm_player.py     # LLM玩家实现
    ├── game/
    │   ├── game_state.py     # 游戏状态管理
    │   └── game_manager.py   # 游戏主控制器
    ├── phases/
    │   ├── night_phase.py    # 夜晚阶段逻辑
    │   ├── day_phase.py      # 白天阶段逻辑
    │   └── mvp_phase.py      # MVP投票阶段
    └── utils/
        └── logger.py         # 日志系统
```

## 🎯 特色功能

### 🤖 智能玩家
- 每个LLM玩家都有独特的角色视角
- 基于游戏规则和当前情况的智能决策
- 支持角色扮演和策略伪装

### 📊 数据分析
- 完整的游戏数据记录
- 投票分布和趋势分析
- MVP评选的详细解释

### 🔄 可扩展性
- 支持添加新角色类型
- 兼容不同LLM API提供商
- 灵活的配置系统

## 🛠️ 技术栈

- **Python 3.8+** - 核心语言
- **Pydantic** - 数据验证
- **Requests** - HTTP客户端
- **JSON Lines** - 日志格式

## 📄 许可证

MIT License - 详见LICENSE文件