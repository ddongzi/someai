"""增强的 CLI 版本 - 支持多中断和 JSON 输入"""
import json
import sys
from typing import Optional, Dict, Any
from pprint import pformat, pprint

from workflow import MyWorkflow
from globals import (
    GraphStatus,
    create_initial_state,
    get_graph_status,
)
from langgraph.types import Command
import logging

logger = logging.getLogger(__name__)


class EnhancedWorkflowCLI:
    """改进的 CLI - 支持多中断、JSON 输入等"""

    def __init__(self):
        self.thread_id = "first_thread"
        self.interrupt_count = 0

    @property
    def config(self):
        return {
            "configurable": {
                "thread_id": self.thread_id
            }
        }

    def get_snapshot(self):
        return my_workflow.graph.get_state(self.config)

    def show_status(self):
        """显示工作流状态"""
        snapshot = self.get_snapshot()
        status = get_graph_status(snapshot)

        print("\n" + "="*60)
        print(f"📊 工作流状态")
        print("="*60)
        print(f"Thread ID: {self.thread_id}")
        print(f"Status: {status}")
        print(f"Next Node: {snapshot.next[0] if snapshot.next else 'END'}")
        print(f"Attempts: {snapshot.values.get('attempts', 0)}")
        
        if snapshot.values.get('tasks'):
            print(f"\nTasks: {snapshot.values['tasks']}")
        
        if snapshot.values.get('current_issue'):
            print(f"\nCurrent Issue: {snapshot.values['current_issue']}")
        
        print("="*60 + "\n")

    def show_full_state(self):
        """显示完整状态"""
        snapshot = self.get_snapshot()
        print("\n" + "="*60)
        print("📋 完整 State:")
        print("="*60)
        pprint(dict(snapshot.values), indent=2, width=80)
        print("="*60 + "\n")

    def start_workflow(self):
        """启动工作流"""
        print("\n🚀 启动工作流...")
        state = create_initial_state()
        try:
            my_workflow.graph.invoke(state, config=self.config)
            print("✅ 工作流已启动")
        except Exception as e:
            print(f"❌ 启动错误: {e}")
            logger.error(f"启动错误: {e}")

    def resume_workflow(self, command: Optional[Dict[str, Any]] = None):
        """继续执行工作流"""
        print("\n▶️  继续执行工作流...")
        
        try:
            if command:
                my_workflow.graph.invoke(
                    Command(resume=command),
                    config=self.config
                )
            else:
                my_workflow.graph.invoke(None, config=self.config)
            
            print("✅ 工作流继续执行完成")
        except Exception as e:
            print(f"❌ 执行错误: {e}")
            logger.error(f"执行错误: {e}")

    def human_interrupt_handler(self):
        """处理人工中断 - 多种输入方式"""
        print("\n" + "="*60)
        print("⚠️  工作流进入中断点")
        print("="*60)
        
        self.interrupt_count += 1
        print(f"\n第 {self.interrupt_count} 次中断\n")

        snapshot = self.get_snapshot()
        print("📊 当前状态:")
        pprint(dict(snapshot.values), indent=2, width=80)

        print("\n" + "-"*60)
        print("请选择操作:")
        print("  1) 批准继续")
        print("  2) 拒绝")
        print("  3) 修改 JSON 数据")
        print("  4) 输入 JSON 文件路径")
        print("  5) 查看完整状态")
        print("  6) 退出")
        print("-"*60)

        while True:
            choice = input("\n请输入选择 (1-6): ").strip()

            if choice == '1':
                print("✅ 批准继续...")
                return {"action": "approved"}

            elif choice == '2':
                print("❌ 已拒绝")
                return {"action": "rejected"}

            elif choice == '3':
                return self._input_json_data("手动编辑")

            elif choice == '4':
                file_path = input("请输入 JSON 文件路径: ").strip()
                return self._load_json_file(file_path)

            elif choice == '5':
                self.show_full_state()
                continue

            elif choice == '6':
                print("⏹️  退出")
                sys.exit(0)

            else:
                print("❌ 无效选择，请重试")

    def _input_json_data(self, mode: str = "修改") -> Dict[str, Any]:
        """JSON 数据输入"""
        snapshot = self.get_snapshot()
        current_state = dict(snapshot.values)

        print(f"\n📝 {mode} JSON 数据")
        print("可直接修改当前 state 或输入新的 JSON")
        print("(输入空行完成)")
        print("-"*60)

        lines = []
        try:
            while True:
                line = input()
                if line.strip() == "":
                    break
                lines.append(line)
        except EOFError:
            pass

        json_str = "\n".join(lines)

        if not json_str.strip():
            # 如果没有输入，显示当前状态并让用户修改
            print("\n当前 State 示例:")
            print(json.dumps(current_state, indent=2, default=str))
            print("\n请粘贴修改后的 JSON (Ctrl+D 或 Ctrl+Z 结束):")
            
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            
            json_str = "\n".join(lines)

        try:
            data = json.loads(json_str)
            print(f"✅ 成功解析 JSON:")
            pprint(data, indent=2, width=80)
            return {"action": "manual_input", "data": data}
        except json.JSONDecodeError as e:
            print(f"❌ JSON 格式错误: {e}")
            return self._input_json_data(mode)

    def _load_json_file(self, file_path: str) -> Dict[str, Any]:
        """从文件加载 JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ 成功加载文件: {file_path}")
            pprint(data, indent=2, width=80)
            return {"action": "manual_input", "data": data}
        except FileNotFoundError:
            print(f"❌ 文件不存在: {file_path}")
            return self.human_interrupt_handler()
        except json.JSONDecodeError as e:
            print(f"❌ JSON 格式错误: {e}")
            return self.human_interrupt_handler()

    def show_history(self, limit: int = 20):
        """显示工作流历史"""
        history = list(my_workflow.graph.get_state_history(self.config))[:limit]

        print("\n" + "="*60)
        print(f"📜 工作流历史 (最后 {len(history)} 个)")
        print("="*60)

        for idx, state in enumerate(history):
            node = state.next[0] if state.next else "END"
            print(f"  [{idx}] → {node}")

        print("="*60 + "\n")

    def interactive_menu(self):
        """交互菜单"""
        while True:
            print("\n" + "="*60)
            print("🎮 工作流管理菜单")
            print("="*60)
            print("  1) 查看状态")
            print("  2) 查看完整 State")
            print("  3) 启动工作流")
            print("  4) 继续执行")
            print("  5) 处理中断")
            print("  6) 查看历史")
            print("  7) 刷新状态")
            print("  0) 退出")
            print("="*60)

            choice = input("\n请选择 (0-7): ").strip()

            if choice == '1':
                self.show_status()

            elif choice == '2':
                self.show_full_state()

            elif choice == '3':
                self.start_workflow()

            elif choice == '4':
                self.resume_workflow()

            elif choice == '5':
                command = self.human_interrupt_handler()
                self.resume_workflow(command)

            elif choice == '6':
                limit = input("显示最后几条历史 (默认20): ").strip()
                try:
                    self.show_history(int(limit) if limit else 20)
                except ValueError:
                    self.show_history()

            elif choice == '7':
                self.show_status()

            elif choice == '0':
                print("\n👋 再见!")
                sys.exit(0)

            else:
                print("❌ 无效选择")

    @staticmethod
    def quick_mode():
        """快速模式 - 启动并监视"""
        cli = EnhancedWorkflowCLI()
        
        print("🚀 快速启动模式")
        cli.start_workflow()
        
        while True:
            cli.show_status()
            
            snapshot = cli.get_snapshot()
            status = get_graph_status(snapshot)
            
            if status == "completed":
                print("🎉 工作流已完成!")
                break
            
            elif status == "waiting":
                print("⏸️  工作流已中断，需要人工干预")
                command = cli.human_interrupt_handler()
                cli.resume_workflow(command)
            
            else:
                input("按 Enter 继续...")


def main():
    """主程序"""
    import argparse
    
    parser = argparse.ArgumentParser(description="工作流管理 CLI")
    parser.add_argument(
        "mode",
        nargs="?",
        default="menu",
        choices=["menu", "quick", "status", "start", "resume"],
        help="运行模式"
    )
    parser.add_argument("--thread-id", help="线程 ID")
    parser.add_argument("--json-input", help="JSON 输入文件路径")
    
    args = parser.parse_args()
    
    cli = EnhancedWorkflowCLI()
    
    if args.thread_id:
        cli.thread_id = args.thread_id
    
    if args.mode == "menu":
        cli.interactive_menu()
    
    elif args.mode == "quick":
        cli.quick_mode()
    
    elif args.mode == "status":
        cli.show_status()
    
    elif args.mode == "start":
        cli.start_workflow()
    
    elif args.mode == "resume":
        if args.json_input:
            command = cli._load_json_file(args.json_input)
        else:
            command = cli.human_interrupt_handler()
        
        cli.resume_workflow(command)


if __name__ == "__main__":
    main()
