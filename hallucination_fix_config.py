#!/usr/bin/env python3
"""
LLM幻觉修复系统配置文件
提供可调整的配置选项和调试工具
"""

from dataclasses import dataclass
from typing import Dict, List, Any
import json


@dataclass
class HallucinationFixConfig:
    """幻觉修复系统配置"""
    
    # 检测严格程度 (0.0-1.0, 1.0最严格)
    detection_strictness: float = 0.8
    
    # 是否启用自动修正
    enable_auto_correction: bool = True
    
    # 是否启用发言质量监控
    enable_quality_monitoring: bool = True
    
    # 是否启用详细调试输出
    enable_debug_output: bool = False
    
    # 是否启用第一轮特殊约束
    enable_first_round_constraints: bool = True
    
    # 身份约束严格程度
    identity_constraint_level: str = "strict"  # "loose", "normal", "strict"
    
    # 时间线约束严格程度
    temporal_constraint_level: str = "strict"  # "loose", "normal", "strict"
    
    # 事件引用约束严格程度
    event_constraint_level: str = "normal"  # "loose", "normal", "strict"
    
    # 质量分数阈值
    quality_score_threshold: float = 0.6
    
    # 是否允许狼人策略性假跳
    allow_werewolf_fake_claims: bool = True
    
    # 修正重试次数
    correction_retry_limit: int = 2
    
    # 日志保留天数
    log_retention_days: int = 7
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "detection_strictness": self.detection_strictness,
            "enable_auto_correction": self.enable_auto_correction,
            "enable_quality_monitoring": self.enable_quality_monitoring,
            "enable_debug_output": self.enable_debug_output,
            "enable_first_round_constraints": self.enable_first_round_constraints,
            "identity_constraint_level": self.identity_constraint_level,
            "temporal_constraint_level": self.temporal_constraint_level,
            "event_constraint_level": self.event_constraint_level,
            "quality_score_threshold": self.quality_score_threshold,
            "allow_werewolf_fake_claims": self.allow_werewolf_fake_claims,
            "correction_retry_limit": self.correction_retry_limit,
            "log_retention_days": self.log_retention_days
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HallucinationFixConfig':
        """从字典创建配置"""
        return cls(**data)
    
    def save_to_file(self, filename: str = "hallucination_fix_config.json"):
        """保存配置到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, filename: str = "hallucination_fix_config.json") -> 'HallucinationFixConfig':
        """从文件加载配置"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except FileNotFoundError:
            print(f"配置文件 {filename} 不存在，使用默认配置")
            return cls()
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            return cls()


class HallucinationFixDebugger:
    """幻觉修复系统调试工具"""
    
    def __init__(self, config: HallucinationFixConfig = None):
        self.config = config or HallucinationFixConfig()
        self.debug_logs = []
    
    def log_debug(self, category: str, message: str, data: Dict[str, Any] = None):
        """记录调试信息"""
        if self.config.enable_debug_output:
            debug_entry = {
                "timestamp": "current",
                "category": category,
                "message": message,
                "data": data or {}
            }
            self.debug_logs.append(debug_entry)
            print(f"🔍 DEBUG [{category}]: {message}")
            if data and self.config.enable_debug_output:
                print(f"    数据: {data}")
    
    def log_validation_result(self, player_id: int, player_name: str, speech: str, 
                            validation_result: Dict[str, Any]):
        """记录验证结果"""
        self.log_debug(
            "VALIDATION",
            f"玩家 {player_name}({player_id}) 发言验证",
            {
                "speech_length": len(speech),
                "is_valid": validation_result["is_valid"],
                "issues_count": len(validation_result.get("issues", [])),
                "issues": validation_result.get("issues", [])
            }
        )
    
    def log_correction_applied(self, player_id: int, player_name: str, 
                             original: str, corrected: str, issues: List[str]):
        """记录修正应用"""
        self.log_debug(
            "CORRECTION",
            f"玩家 {player_name}({player_id}) 发言已修正",
            {
                "original_length": len(original),
                "corrected_length": len(corrected),
                "issues_fixed": issues,
                "correction_ratio": len(corrected) / len(original) if len(original) > 0 else 0
            }
        )
    
    def log_quality_assessment(self, player_id: int, player_name: str, 
                             quality_score: float, details: Dict[str, Any]):
        """记录质量评估"""
        self.log_debug(
            "QUALITY",
            f"玩家 {player_name}({player_id}) 发言质量评估",
            {
                "quality_score": quality_score,
                "threshold": self.config.quality_score_threshold,
                "meets_threshold": quality_score >= self.config.quality_score_threshold,
                **details
            }
        )
    
    def generate_debug_report(self) -> Dict[str, Any]:
        """生成调试报告"""
        if not self.debug_logs:
            return {"message": "暂无调试数据"}
        
        # 按类别统计
        categories = {}
        for log in self.debug_logs:
            category = log["category"]
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        # 统计验证结果
        validation_logs = [log for log in self.debug_logs if log["category"] == "VALIDATION"]
        total_validations = len(validation_logs)
        valid_speeches = sum(1 for log in validation_logs 
                           if log["data"].get("is_valid", False))
        
        # 统计修正结果
        correction_logs = [log for log in self.debug_logs if log["category"] == "CORRECTION"]
        total_corrections = len(correction_logs)
        
        # 统计质量评估
        quality_logs = [log for log in self.debug_logs if log["category"] == "QUALITY"]
        if quality_logs:
            avg_quality = sum(log["data"]["quality_score"] for log in quality_logs) / len(quality_logs)
            quality_above_threshold = sum(1 for log in quality_logs 
                                        if log["data"]["meets_threshold"])
        else:
            avg_quality = 0
            quality_above_threshold = 0
        
        return {
            "total_debug_entries": len(self.debug_logs),
            "categories": categories,
            "validation_stats": {
                "total_validations": total_validations,
                "valid_speeches": valid_speeches,
                "validation_rate": valid_speeches / total_validations if total_validations > 0 else 0
            },
            "correction_stats": {
                "total_corrections": total_corrections,
                "correction_rate": total_corrections / total_validations if total_validations > 0 else 0
            },
            "quality_stats": {
                "total_assessments": len(quality_logs),
                "average_quality_score": round(avg_quality, 2),
                "above_threshold_count": quality_above_threshold,
                "above_threshold_rate": quality_above_threshold / len(quality_logs) if quality_logs else 0
            }
        }
    
    def print_debug_report(self):
        """打印调试报告"""
        report = self.generate_debug_report()
        
        print("\n" + "=" * 50)
        print("🔍 幻觉修复系统调试报告")
        print("=" * 50)
        
        if "message" in report:
            print(report["message"])
            return
        
        print(f"总调试条目: {report['total_debug_entries']}")
        print(f"\n📊 分类统计:")
        for category, count in report["categories"].items():
            print(f"  {category}: {count}")
        
        validation_stats = report["validation_stats"]
        print(f"\n✅ 验证统计:")
        print(f"  总验证次数: {validation_stats['total_validations']}")
        print(f"  通过验证: {validation_stats['valid_speeches']}")
        print(f"  验证通过率: {validation_stats['validation_rate']:.1%}")
        
        correction_stats = report["correction_stats"]
        print(f"\n🔧 修正统计:")
        print(f"  总修正次数: {correction_stats['total_corrections']}")
        print(f"  修正率: {correction_stats['correction_rate']:.1%}")
        
        quality_stats = report["quality_stats"]
        print(f"\n📈 质量统计:")
        print(f"  总评估次数: {quality_stats['total_assessments']}")
        print(f"  平均质量分数: {quality_stats['average_quality_score']}")
        print(f"  达标数量: {quality_stats['above_threshold_count']}")
        print(f"  达标率: {quality_stats['above_threshold_rate']:.1%}")
    
    def clear_debug_logs(self):
        """清空调试日志"""
        self.debug_logs.clear()
        print("🗑️ 调试日志已清空")


class HallucinationFixManager:
    """幻觉修复系统管理器"""
    
    def __init__(self, config_file: str = "hallucination_fix_config.json"):
        self.config_file = config_file
        self.config = HallucinationFixConfig.load_from_file(config_file)
        self.debugger = HallucinationFixDebugger(self.config)
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                print(f"✅ 配置已更新: {key} = {value}")
            else:
                print(f"❌ 未知配置项: {key}")
    
    def save_config(self):
        """保存配置"""
        self.config.save_to_file(self.config_file)
        print(f"💾 配置已保存到 {self.config_file}")
    
    def reload_config(self):
        """重新加载配置"""
        self.config = HallucinationFixConfig.load_from_file(self.config_file)
        self.debugger.config = self.config
        print(f"🔄 配置已从 {self.config_file} 重新加载")
    
    def print_current_config(self):
        """打印当前配置"""
        print("\n" + "=" * 40)
        print("⚙️ 当前幻觉修复系统配置")
        print("=" * 40)
        
        config_dict = self.config.to_dict()
        for key, value in config_dict.items():
            print(f"  {key}: {value}")
    
    def run_interactive_config(self):
        """运行交互式配置"""
        print("\n🛠️ 交互式配置模式")
        print("输入 'help' 查看可用命令，输入 'exit' 退出")
        
        while True:
            try:
                command = input("\n配置> ").strip().lower()
                
                if command == 'exit':
                    break
                elif command == 'help':
                    self._print_config_help()
                elif command == 'show':
                    self.print_current_config()
                elif command == 'save':
                    self.save_config()
                elif command == 'reload':
                    self.reload_config()
                elif command == 'debug':
                    self.debugger.print_debug_report()
                elif command.startswith('set '):
                    self._handle_set_command(command)
                else:
                    print("❌ 未知命令，输入 'help' 查看帮助")
            
            except KeyboardInterrupt:
                print("\n👋 退出配置模式")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")
    
    def _print_config_help(self):
        """打印配置帮助"""
        print("\n📖 可用命令:")
        print("  help     - 显示此帮助")
        print("  show     - 显示当前配置")
        print("  save     - 保存配置到文件")
        print("  reload   - 从文件重新加载配置")
        print("  debug    - 显示调试报告")
        print("  set <key> <value> - 设置配置项")
        print("  exit     - 退出配置模式")
        
        print("\n⚙️ 可配置项:")
        print("  detection_strictness (0.0-1.0)")
        print("  enable_auto_correction (true/false)")
        print("  enable_quality_monitoring (true/false)")
        print("  enable_debug_output (true/false)")
        print("  identity_constraint_level (loose/normal/strict)")
        print("  quality_score_threshold (0.0-1.0)")
    
    def _handle_set_command(self, command: str):
        """处理set命令"""
        parts = command.split()
        if len(parts) != 3:
            print("❌ 用法: set <key> <value>")
            return
        
        key = parts[1]
        value_str = parts[2]
        
        # 类型转换
        if value_str.lower() in ['true', 'false']:
            value = value_str.lower() == 'true'
        elif value_str.replace('.', '').isdigit():
            value = float(value_str) if '.' in value_str else int(value_str)
        else:
            value = value_str
        
        self.update_config(**{key: value})


def main():
    """主函数 - 演示配置和调试工具"""
    print("🛠️ LLM幻觉修复系统配置和调试工具")
    
    # 创建管理器
    manager = HallucinationFixManager()
    
    # 显示当前配置
    manager.print_current_config()
    
    # 模拟一些调试数据
    debugger = manager.debugger
    debugger.log_validation_result(1, "Alice", "我是预言家", {"is_valid": False, "issues": ["身份错误"]})
    debugger.log_correction_applied(1, "Alice", "我是预言家", "我是村民", ["身份错误"])
    debugger.log_quality_assessment(1, "Alice", 0.7, {"meets_threshold": True})
    
    # 显示调试报告
    debugger.print_debug_report()
    
    # 启动交互式配置（可选）
    # manager.run_interactive_config()


if __name__ == "__main__":
    main()