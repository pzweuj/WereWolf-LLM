#!/usr/bin/env python3
"""
随机重新分配玩家编号和角色的脚本

使用方法：
    python reshuffle_config.py [input_file] [output_file]

示例：
    python reshuffle_config.py game_config.json game_config_shuffled.json
    python reshuffle_config.py                 # 使用默认文件
"""

import json
import random
import sys
import os
from pathlib import Path


def shuffle_players_config(input_config: dict) -> dict:
    """重新随机分配玩家编号和角色"""
    original_players = input_config["players"]
    
    # 提取所有API配置信息
    api_configs = []
    for player in original_players:
        api_configs.append({
            "api_url": player["api_url"],
            "api_key": player["api_key"],
            "model": player["model"]
        })
    
    # 定义角色配置
    roles = [
        "werewolf", "werewolf", "werewolf",  # 3个狼人
        "seer",                             # 1个预言家
        "witch",                            # 1个女巫
        "hunter",                           # 1个猎人
        "villager", "villager", "villager", "villager"  # 4个村民
    ]
    
    # 随机打乱角色顺序
    shuffled_roles = roles.copy()
    random.shuffle(shuffled_roles)
    
    # 随机打乱API配置顺序
    shuffled_apis = api_configs.copy()
    random.shuffle(shuffled_apis)
    
    # 生成新的玩家配置
    new_players = []
    
    # 提取原始名称并打乱顺序
    original_names = [player["name"] for player in original_players]
    shuffled_names = original_names.copy()
    random.shuffle(shuffled_names)
    
    # 将角色、API配置和打乱后的名称进行配对，重新分配ID
    for i, (role, api_config, name) in enumerate(zip(shuffled_roles, shuffled_apis, shuffled_names), 1):
        new_player = {
            "id": i,  # 重新分配ID从1开始
            "name": name,  # 使用打乱后的名称，保持原始名称不变但重新分配
            "role": role,
            "api_url": api_config["api_url"],
            "api_key": api_config["api_key"],
            "model": api_config["model"]
        }
        new_players.append(new_player)
    
    return {
        "players": new_players,
        "description": "重新随机分配角色后的游戏配置",
        "shuffled_at": "随机生成",
        "original_config": input_config.get("description", "原始配置")
    }




def load_config(file_path: str) -> dict:
    """加载配置文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误：JSON格式错误 - {e}")
        sys.exit(1)


def save_config(config: dict, file_path: str):
    """保存配置文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"配置已保存到：{file_path}")
    except Exception as e:
        print(f"保存文件时出错：{e}")
        sys.exit(1)


def display_role_distribution(config: dict):
    """显示角色分配情况"""
    players = config["players"]
    role_counts = {}
    
    for player in players:
        role = player["role"]
        role_counts[role] = role_counts.get(role, 0) + 1
    
    print("\n=== 角色分配结果 ===")
    print(f"狼人: {role_counts.get('werewolf', 0)}名")
    print(f"预言家: {role_counts.get('seer', 0)}名")
    print(f"女巫: {role_counts.get('witch', 0)}名")
    print(f"猎人: {role_counts.get('hunter', 0)}名")
    print(f"村民: {role_counts.get('villager', 0)}名")
    
    print("\n=== 玩家详情 ===")
    for player in sorted(players, key=lambda x: x["id"]):
        print(f"{player['id']}. {player['name']} -> {player['role']}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="重新随机分配狼人杀玩家角色")
    parser.add_argument(
        "input_file",
        nargs="?",
        default="game_config.json",
        help="输入配置文件路径 (默认: game_config.json)"
    )
    parser.add_argument(
        "output_file", 
        nargs="?",
        default=None,
        help="输出配置文件路径 (默认: 原文件名 + _shuffled.json)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机种子 (用于可重复的结果)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="仅预览结果，不保存文件"
    )
    
    args = parser.parse_args()
    
    # 设置随机种子
    if args.seed is not None:
        random.seed(args.seed)
        print(f"使用随机种子: {args.seed}")
    
    # 确定输出文件名
    if args.output_file is None:
        input_path = Path(args.input_file)
        stem = input_path.stem
        suffix = input_path.suffix
        args.output_file = f"{stem}_shuffled{suffix}"
    
    # 加载原始配置
    print(f"加载配置: {args.input_file}")
    original_config = load_config(args.input_file)
    
    # 生成新配置
    new_config = shuffle_players_config(original_config)
    
    # 显示结果
    display_role_distribution(new_config)
    
    if args.preview:
        print("\n[预览模式] - 未保存文件")
    else:
        save_config(new_config, args.output_file)
        print(f"\n[成功] 新配置已保存到: {args.output_file}")
        print(f"使用命令运行: python main.py {args.output_file}")


if __name__ == "__main__":
    main()