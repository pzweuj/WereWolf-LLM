"""
Command-line interface for configuration management.
Provides interactive configuration management, validation, and monitoring tools.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .config_manager import get_config_manager, ConfigManager
from .config_validator import get_validator, ValidationReport
from .runtime_updater import get_runtime_updater, UpdateStatus
from ..models.hallucination_models import HallucinationReductionConfig


class ConfigCLI:
    """Command-line interface for configuration management."""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.validator = get_validator()
        self.runtime_updater = get_runtime_updater(self.config_manager)
    
    def run(self):
        """Run the CLI with command-line arguments."""
        parser = self._create_parser()
        args = parser.parse_args()
        
        if hasattr(args, 'func'):
            try:
                args.func(args)
            except KeyboardInterrupt:
                print("\n操作已取消")
                sys.exit(1)
            except Exception as e:
                print(f"错误: {e}")
                sys.exit(1)
        else:
            parser.print_help()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            description="幻觉减少系统配置管理工具",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        subparsers = parser.add_subparsers(dest='command', help='可用命令')
        
        # Show current configuration
        show_parser = subparsers.add_parser('show', help='显示当前配置')
        show_parser.add_argument('--format', choices=['json', 'yaml', 'table'], 
                               default='table', help='输出格式')
        show_parser.set_defaults(func=self.cmd_show)
        
        # Validate configuration
        validate_parser = subparsers.add_parser('validate', help='验证配置')
        validate_parser.add_argument('--file', help='配置文件路径')
        validate_parser.add_argument('--fix', action='store_true', help='自动修复问题')
        validate_parser.set_defaults(func=self.cmd_validate)
        
        # Update configuration
        update_parser = subparsers.add_parser('update', help='更新配置')
        update_parser.add_argument('--set', action='append', metavar='KEY=VALUE',
                                 help='设置配置项 (可多次使用)')
        update_parser.add_argument('--file', help='从文件加载配置')
        update_parser.add_argument('--dry-run', action='store_true', help='仅显示变更，不实际应用')
        update_parser.set_defaults(func=self.cmd_update)
        
        # Monitor updates
        monitor_parser = subparsers.add_parser('monitor', help='监控配置更新')
        monitor_parser.add_argument('--follow', action='store_true', help='持续监控')
        monitor_parser.set_defaults(func=self.cmd_monitor)
        
        # Rollback update
        rollback_parser = subparsers.add_parser('rollback', help='回滚配置更新')
        rollback_parser.add_argument('update_id', help='更新ID')
        rollback_parser.set_defaults(func=self.cmd_rollback)
        
        # Interactive mode
        interactive_parser = subparsers.add_parser('interactive', help='交互式配置模式')
        interactive_parser.set_defaults(func=self.cmd_interactive)
        
        # Export configuration
        export_parser = subparsers.add_parser('export', help='导出配置')
        export_parser.add_argument('--format', choices=['json', 'yaml'], 
                                 default='json', help='导出格式')
        export_parser.add_argument('--output', help='输出文件路径')
        export_parser.set_defaults(func=self.cmd_export)
        
        # Import configuration
        import_parser = subparsers.add_parser('import', help='导入配置')
        import_parser.add_argument('file', help='配置文件路径')
        import_parser.add_argument('--format', choices=['json', 'yaml'], help='文件格式')
        import_parser.add_argument('--validate-only', action='store_true', help='仅验证，不导入')
        import_parser.set_defaults(func=self.cmd_import)
        
        # Reset to defaults
        reset_parser = subparsers.add_parser('reset', help='重置为默认配置')
        reset_parser.add_argument('--confirm', action='store_true', help='确认重置')
        reset_parser.set_defaults(func=self.cmd_reset)
        
        return parser
    
    def cmd_show(self, args):
        """Show current configuration."""
        config = self.config_manager.get_config()
        
        if args.format == 'json':
            config_dict = config.__dict__
            print(json.dumps(config_dict, indent=2, ensure_ascii=False))
        elif args.format == 'yaml':
            try:
                import yaml
                config_dict = config.__dict__
                print(yaml.dump(config_dict, default_flow_style=False, allow_unicode=True))
            except ImportError:
                print("PyYAML未安装，使用JSON格式:")
                config_dict = config.__dict__
                print(json.dumps(config_dict, indent=2, ensure_ascii=False))
        else:  # table format
            self._print_config_table(config)
    
    def _print_config_table(self, config: HallucinationReductionConfig):
        """Print configuration in table format."""
        print("\n" + "=" * 60)
        print("🔧 幻觉减少系统配置")
        print("=" * 60)
        
        sections = {
            "检测配置": [
                ("detection_strictness", "检测严格程度"),
                ("enable_multi_layer_detection", "启用多层检测"),
                ("max_detection_time", "最大检测时间(秒)")
            ],
            "修正配置": [
                ("enable_auto_correction", "启用自动修正"),
                ("max_correction_attempts", "最大修正尝试次数"),
                ("correction_quality_threshold", "修正质量阈值")
            ],
            "上下文配置": [
                ("max_speech_history_length", "最大发言历史长度"),
                ("enable_reality_anchors", "启用现实锚点"),
                ("context_validation_enabled", "启用上下文验证")
            ],
            "报告配置": [
                ("enable_detailed_logging", "启用详细日志"),
                ("report_generation_enabled", "启用报告生成"),
                ("export_format", "导出格式")
            ],
            "性能配置": [
                ("enable_async_processing", "启用异步处理"),
                ("cache_detection_results", "缓存检测结果"),
                ("max_concurrent_detections", "最大并发检测数")
            ]
        }
        
        for section_name, fields in sections.items():
            print(f"\n📋 {section_name}:")
            for field_name, display_name in fields:
                value = getattr(config, field_name, "未设置")
                print(f"  {display_name:.<30} {value}")
    
    def cmd_validate(self, args):
        """Validate configuration."""
        if args.file:
            validation_report = self.validator.validate_config_file(args.file)
            print(f"\n验证配置文件: {args.file}")
        else:
            config = self.config_manager.get_config()
            validation_report = self.validator.validate_config(config)
            print("\n验证当前配置:")
        
        self._print_validation_report(validation_report)
        
        if args.fix and not validation_report.is_valid:
            self._attempt_auto_fix(validation_report)
    
    def _print_validation_report(self, report: ValidationReport):
        """Print validation report."""
        print("\n" + "=" * 50)
        print("📊 配置验证报告")
        print("=" * 50)
        
        # Status
        status_icon = "✅" if report.is_valid else "❌"
        print(f"\n状态: {status_icon} {'有效' if report.is_valid else '无效'}")
        print(f"评分: {report.score:.2f}/1.0")
        print(f"摘要: {report.summary}")
        
        if report.issues:
            print(f"\n发现 {len(report.issues)} 个问题:")
            
            # Group issues by level
            errors = [issue for issue in report.issues if issue.level == "error"]
            warnings = [issue for issue in report.issues if issue.level == "warning"]
            infos = [issue for issue in report.issues if issue.level == "info"]
            
            for level, issues, icon in [("错误", errors, "❌"), ("警告", warnings, "⚠️"), ("信息", infos, "ℹ️")]:
                if issues:
                    print(f"\n{icon} {level} ({len(issues)}):")
                    for issue in issues:
                        print(f"  • {issue.field}: {issue.message}")
                        if issue.current_value is not None:
                            print(f"    当前值: {issue.current_value}")
                        if issue.suggested_value is not None:
                            print(f"    建议值: {issue.suggested_value}")
    
    def _attempt_auto_fix(self, validation_report: ValidationReport):
        """Attempt to automatically fix configuration issues."""
        print("\n🔧 尝试自动修复配置问题...")
        
        config = self.config_manager.get_config()
        config_dict = config.__dict__
        
        fixed_config, fixes_applied = self.validator.fix_config_issues(config_dict, validation_report)
        
        if fixes_applied:
            print(f"\n应用了 {len(fixes_applied)} 个修复:")
            for fix in fixes_applied:
                print(f"  • {fix}")
            
            # Apply fixes
            changes = {k: v for k, v in fixed_config.items() if k in config_dict and config_dict[k] != v}
            if changes:
                success = self.config_manager.update_config(**changes)
                if success:
                    print("\n✅ 配置修复已应用")
                else:
                    print("\n❌ 配置修复应用失败")
        else:
            print("\n无法自动修复发现的问题")
    
    def cmd_update(self, args):
        """Update configuration."""
        changes = {}
        
        # Parse --set arguments
        if args.set:
            for setting in args.set:
                if '=' not in setting:
                    print(f"错误: 无效的设置格式 '{setting}' (应为 KEY=VALUE)")
                    return
                
                key, value = setting.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Type conversion
                changes[key] = self._parse_value(value)
        
        # Load from file
        if args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    file_changes = json.load(f)
                changes.update(file_changes)
            except Exception as e:
                print(f"错误: 无法读取配置文件 {args.file}: {e}")
                return
        
        if not changes:
            print("错误: 没有指定要更新的配置项")
            return
        
        # Analyze impact
        impact_analysis = self.runtime_updater.analyze_update_impact(changes)
        self._print_impact_analysis(impact_analysis)
        
        if args.dry_run:
            print("\n🔍 预演模式 - 不会实际应用更改")
            return
        
        # Confirm if high impact
        if impact_analysis['overall_impact'] in ['high', 'critical']:
            if not self._confirm_update(impact_analysis):
                print("更新已取消")
                return
        
        # Apply update
        print("\n🔄 应用配置更新...")
        update_id = self.runtime_updater.request_update(
            changes, 
            requester="cli", 
            reason="CLI update"
        )
        
        print(f"更新请求已提交: {update_id}")
        
        # Wait for completion
        self._wait_for_update(update_id)
    
    def _parse_value(self, value_str: str):
        """Parse a string value to appropriate type."""
        # Boolean values
        if value_str.lower() in ['true', 'false']:
            return value_str.lower() == 'true'
        
        # Numeric values
        if value_str.replace('.', '').replace('-', '').isdigit():
            return float(value_str) if '.' in value_str else int(value_str)
        
        # String values
        return value_str
    
    def _print_impact_analysis(self, analysis: Dict[str, Any]):
        """Print impact analysis."""
        print("\n📈 变更影响分析:")
        print(f"  总体影响: {analysis['overall_impact']}")
        print(f"  需要重启: {'是' if analysis['restart_required'] else '否'}")
        print(f"  性能影响: {analysis['performance_impact']}")
        
        if analysis['affected_components']:
            print(f"  影响组件: {', '.join(analysis['affected_components'])}")
        
        if analysis['recommendations']:
            print("\n💡 建议:")
            for rec in analysis['recommendations']:
                print(f"  • {rec}")
    
    def _confirm_update(self, impact_analysis: Dict[str, Any]) -> bool:
        """Confirm high-impact update with user."""
        print(f"\n⚠️ 此更新具有{impact_analysis['overall_impact']}影响")
        
        if impact_analysis['restart_required']:
            print("⚠️ 此更新可能需要系统重启")
        
        while True:
            response = input("\n是否继续? (y/n): ").strip().lower()
            if response in ['y', 'yes', '是']:
                return True
            elif response in ['n', 'no', '否']:
                return False
            else:
                print("请输入 y 或 n")
    
    def _wait_for_update(self, update_id: str, timeout: int = 30):
        """Wait for update completion."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            update = self.runtime_updater.get_update_status(update_id)
            if not update:
                print("❌ 无法获取更新状态")
                return
            
            if update.status == UpdateStatus.COMPLETED:
                print("✅ 配置更新完成")
                return
            elif update.status == UpdateStatus.FAILED:
                print(f"❌ 配置更新失败: {update.error_message}")
                return
            elif update.status == UpdateStatus.ROLLED_BACK:
                print("🔄 配置更新已回滚")
                return
            
            print(f"⏳ 更新状态: {update.status.value}")
            time.sleep(2)
        
        print("⏰ 更新超时，请使用 monitor 命令检查状态")
    
    def cmd_monitor(self, args):
        """Monitor configuration updates."""
        if args.follow:
            print("📊 持续监控配置更新 (按 Ctrl+C 退出)...")
            try:
                while True:
                    self._print_update_status()
                    time.sleep(5)
            except KeyboardInterrupt:
                print("\n监控已停止")
        else:
            self._print_update_status()
    
    def _print_update_status(self):
        """Print current update status."""
        pending_updates = self.runtime_updater.get_pending_updates()
        recent_history = self.runtime_updater.get_update_history(limit=5)
        
        print(f"\n📊 配置更新状态 ({datetime.now().strftime('%H:%M:%S')})")
        print("=" * 50)
        
        if pending_updates:
            print(f"\n⏳ 待处理更新 ({len(pending_updates)}):")
            for update in pending_updates:
                print(f"  • {update.update_id}: {update.status.value}")
                print(f"    请求者: {update.requester}")
                print(f"    时间: {update.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("\n✅ 无待处理更新")
        
        if recent_history:
            print(f"\n📜 最近更新历史:")
            for update in recent_history:
                status_icon = {"completed": "✅", "failed": "❌", "rolled_back": "🔄"}.get(update.status.value, "❓")
                print(f"  {status_icon} {update.update_id}: {update.status.value}")
                print(f"    时间: {update.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def cmd_rollback(self, args):
        """Rollback a configuration update."""
        update_id = args.update_id
        
        # Get rollback info
        rollback_info = self.runtime_updater.get_rollback_info(update_id)
        if not rollback_info:
            print(f"❌ 无法回滚更新 {update_id}: 没有可用的回滚信息")
            return
        
        print(f"\n🔄 准备回滚更新: {update_id}")
        print(f"快照时间: {rollback_info['snapshot_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("将要回滚的更改:")
        for key, value in rollback_info['changes_to_rollback'].items():
            print(f"  • {key}: {value}")
        
        # Confirm rollback
        while True:
            response = input("\n确认回滚? (y/n): ").strip().lower()
            if response in ['y', 'yes', '是']:
                break
            elif response in ['n', 'no', '否']:
                print("回滚已取消")
                return
            else:
                print("请输入 y 或 n")
        
        # Perform rollback
        success = self.runtime_updater.rollback_update(update_id)
        if success:
            print("✅ 配置回滚成功")
        else:
            print("❌ 配置回滚失败")
    
    def cmd_interactive(self, args):
        """Interactive configuration mode."""
        print("\n🛠️ 交互式配置模式")
        print("输入 'help' 查看可用命令，输入 'exit' 退出")
        
        while True:
            try:
                command = input("\n配置> ").strip()
                
                if command == 'exit':
                    break
                elif command == 'help':
                    self._print_interactive_help()
                elif command == 'show':
                    config = self.config_manager.get_config()
                    self._print_config_table(config)
                elif command == 'validate':
                    config = self.config_manager.get_config()
                    validation_report = self.validator.validate_config(config)
                    self._print_validation_report(validation_report)
                elif command.startswith('set '):
                    self._handle_interactive_set(command)
                elif command == 'save':
                    success = self.config_manager.save_config()
                    print("✅ 配置已保存" if success else "❌ 配置保存失败")
                elif command == 'reload':
                    success = self.config_manager.reload_config()
                    print("✅ 配置已重新加载" if success else "❌ 配置重新加载失败")
                elif command == 'history':
                    history = self.runtime_updater.get_update_history(limit=10)
                    self._print_update_history(history)
                else:
                    print("❌ 未知命令，输入 'help' 查看帮助")
            
            except KeyboardInterrupt:
                print("\n👋 退出交互模式")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")
    
    def _print_interactive_help(self):
        """Print interactive mode help."""
        print("\n📖 交互模式命令:")
        print("  help       - 显示此帮助")
        print("  show       - 显示当前配置")
        print("  validate   - 验证当前配置")
        print("  set <key> <value> - 设置配置项")
        print("  save       - 保存配置到文件")
        print("  reload     - 从文件重新加载配置")
        print("  history    - 显示更新历史")
        print("  exit       - 退出交互模式")
    
    def _handle_interactive_set(self, command: str):
        """Handle interactive set command."""
        parts = command.split()
        if len(parts) != 3:
            print("❌ 用法: set <key> <value>")
            return
        
        key = parts[1]
        value = self._parse_value(parts[2])
        
        success = self.config_manager.update_config(**{key: value})
        if success:
            print(f"✅ 配置已更新: {key} = {value}")
        else:
            print(f"❌ 配置更新失败: {key}")
    
    def _print_update_history(self, history):
        """Print update history."""
        if not history:
            print("📜 无更新历史")
            return
        
        print(f"\n📜 最近 {len(history)} 次更新:")
        for update in history:
            status_icon = {
                "completed": "✅", 
                "failed": "❌", 
                "rolled_back": "🔄"
            }.get(update.status.value, "❓")
            
            print(f"\n{status_icon} {update.update_id}")
            print(f"  状态: {update.status.value}")
            print(f"  时间: {update.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  请求者: {update.requester}")
            if update.error_message:
                print(f"  错误: {update.error_message}")
    
    def cmd_export(self, args):
        """Export configuration."""
        try:
            config_str = self.config_manager.export_config(args.format)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(config_str)
                print(f"✅ 配置已导出到 {args.output}")
            else:
                print(config_str)
                
        except Exception as e:
            print(f"❌ 导出失败: {e}")
    
    def cmd_import(self, args):
        """Import configuration."""
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                config_str = f.read()
            
            # Determine format
            format_type = args.format
            if not format_type:
                format_type = 'yaml' if args.file.endswith('.yaml') or args.file.endswith('.yml') else 'json'
            
            if args.validate_only:
                # Just validate
                if format_type == 'json':
                    config_data = json.loads(config_str)
                else:
                    import yaml
                    config_data = yaml.safe_load(config_str)
                
                validation_report = self.validator.validate_config(config_data)
                self._print_validation_report(validation_report)
            else:
                # Import
                success = self.config_manager.import_config(config_str, format_type)
                if success:
                    print(f"✅ 配置已从 {args.file} 导入")
                else:
                    print(f"❌ 配置导入失败")
                    
        except Exception as e:
            print(f"❌ 导入失败: {e}")
    
    def cmd_reset(self, args):
        """Reset configuration to defaults."""
        if not args.confirm:
            print("⚠️ 此操作将重置所有配置为默认值")
            while True:
                response = input("确认重置? (y/n): ").strip().lower()
                if response in ['y', 'yes', '是']:
                    break
                elif response in ['n', 'no', '否']:
                    print("重置已取消")
                    return
                else:
                    print("请输入 y 或 n")
        
        success = self.config_manager.reset_to_defaults()
        if success:
            print("✅ 配置已重置为默认值")
        else:
            print("❌ 配置重置失败")


def main():
    """Main entry point for the CLI."""
    cli = ConfigCLI()
    cli.run()


if __name__ == "__main__":
    main()