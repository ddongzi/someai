"""启动脚本 - 选择运行模式"""
import sys
import subprocess
import argparse
from pathlib import Path




def run_cli(mode="menu", args=None):
    """运行 CLI"""
    cmd = [sys.executable, "user_cli.py", mode]
    
    if args:
        cmd.extend(args)
    
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="工作流管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s server          # 启动 Web UI
  %(prog)s cli             # 启动 CLI 菜单
  %(prog)s cli quick       # 快速启动
  %(prog)s cli status      # 显示状态
        """
    )
    
    subparsers = parser.add_subparsers(dest="mode", help="运行模式")
    
    # Server 模式
    subparsers.add_parser("server", help="启动 FastAPI 服务器 (WEB UI)")
    
    # CLI 模式
    cli_parser = subparsers.add_parser("cli", help="启动 CLI")
    cli_parser.add_argument("cli_mode", nargs="?", default="menu",
                            choices=["menu", "quick", "status", "start", "resume"],
                            help="CLI 运行模式")
    cli_parser.add_argument("--thread-id", help="线程 ID")
    cli_parser.add_argument("--json-input", help="JSON 输入文件")
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        print("""
╔═══════════════════════════════════════════════════════════════╗
║                  🚀 选择启动模式                              ║
╚═══════════════════════════════════════════════════════════════╝

快速启动:
  python run.py server     # WEB UI 模式 (推荐)
  python run.py cli        # CLI 菜单模式

CLI 子模式:
  python run.py cli quick           # 快速启动并监视
  python run.py cli status          # 查看状态
  python run.py cli start           # 启动工作流
  python run.py cli resume          # 继续执行
        """)
        return
    
    if args.mode == "server":
        run_server()
    
    elif args.mode == "cli":
        cli_args = []
        if hasattr(args, 'thread_id') and args.thread_id:
            cli_args.extend(["--thread-id", args.thread_id])
        if hasattr(args, 'json_input') and args.json_input:
            cli_args.extend(["--json-input", args.json_input])
        
        run_cli(args.cli_mode, cli_args)


if __name__ == "__main__":
    main()
