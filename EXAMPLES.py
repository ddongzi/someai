"""示例: 如何使用新的工作流管理系统"""

# ============================================================
# 示例 1: CLI 快速启动
# ============================================================
"""
# 启动工作流并自动监视
python run.py cli quick

# 工作流执行...
# 当遇到 interrupt 时:
# ⚠️  工作流进入中断点
# 
# 第 1 次中断
# 
# 请选择操作:
#   1) 批准继续
#   2) 拒绝
#   3) 修改 JSON 数据
#   4) 输入 JSON 文件路径
#   5) 查看完整状态
#   6) 退出
"""

# ============================================================
# 示例 2: CLI 菜单模式 (多中断)
# ============================================================
"""
# 启动菜单
python run.py cli

# 输出:
# ============================================================
# 🎮 工作流管理菜单
# ============================================================
#   1) 查看状态
#   2) 查看完整 State
#   3) 启动工作流
#   4) 继续执行
#   5) 处理中断
#   6) 查看历史
#   7) 刷新状态
#   0) 退出
# ============================================================
#
# 请选择 (0-7): 3
# 🚀 启动工作流...
# ✅ 工作流已启动
#
# 请选择 (0-7): 1
# ====== 当前状态 ======
# Thread: first_thread
# Status: waiting
# Next: human_node
# =====================
#
# 请选择 (0-7): 5
# ⚠️  工作流进入中断点
# ... 中断处理选项 ...
"""

# ============================================================
# 示例 3: WEB UI 模式
# ============================================================
"""
# 启动服务器
python run.py server

# 浏览器打开:
# http://localhost:8000

# 前端会显示:
# - 工作流状态 (运行中/等待/完成)
# - 下一步节点
# - 尝试次数
# - 事件日志
#
# 人工输入区支持:
# - JSON 数据编辑
# - 批准/拒绝
# - 文本输入
# - 代码修改
"""

# ============================================================
# 示例 4: 从文件恢复工作流
# ============================================================
"""
# 保存状态到文件
python run.py cli menu
# 选择 (2) 查看完整 State
# 复制输出保存到 state.json

# 修改 state.json 后,继续执行:
python run.py cli resume --json-input state.json
"""

# ============================================================
# 示例 5: Python API 调用 (REST)
# ============================================================

import requests
import json

BASE_URL = "http://localhost:8000/api"

def example_rest_api():
    # 1. 获取状态
    print("=" * 60)
    print("获取状态")
    print("=" * 60)
    response = requests.get(f"{BASE_URL}/status")
    status = response.json()
    print(json.dumps(status, indent=2, default=str))
    
    # 2. 启动工作流
    print("\n" + "=" * 60)
    print("启动工作流")
    print("=" * 60)
    response = requests.post(f"{BASE_URL}/start")
    result = response.json()
    print(json.dumps(result, indent=2, default=str))
    
    # 3. 提交人工输入 (JSON)
    print("\n" + "=" * 60)
    print("提交人工输入")
    print("=" * 60)
    human_input = {
        "data": {
            "modified_field": "new_value",
            "decisions": ["approve", "proceed"]
        },
        "action": "manual_input"
    }
    response = requests.post(
        f"{BASE_URL}/human_input",
        json=human_input
    )
    result = response.json()
    print(json.dumps(result, indent=2, default=str))
    
    # 4. 获取历史
    print("\n" + "=" * 60)
    print("获取历史")
    print("=" * 60)
    response = requests.get(f"{BASE_URL}/history?limit=5")
    history = response.json()
    print(json.dumps(history, indent=2, default=str))
    
    # 5. 获取完整快照
    print("\n" + "=" * 60)
    print("获取完整快照")
    print("=" * 60)
    response = requests.get(f"{BASE_URL}/snapshot")
    snapshot = response.json()
    print(json.dumps(snapshot, indent=2, default=str))


# ============================================================
# 示例 6: WebSocket 异步通信
# ============================================================

import asyncio
import websockets
import json

async def example_websocket():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as ws:
        print("✅ 连接成功")
        
        # 1. 获取初始状态
        print("\n📊 获取状态...")
        await ws.send(json.dumps({"type": "get_status"}))
        response = await ws.recv()
        print(f"响应: {response}")
        
        # 2. 启动工作流
        print("\n🚀 启动工作流...")
        await ws.send(json.dumps({"type": "start"}))
        response = await ws.recv()
        print(f"响应: {response}")
        
        # 3. 监听消息 (持续)
        print("\n👂 监听事件...")
        try:
            while True:
                message = await ws.recv()
                data = json.loads(message)
                print(f"事件: {data.get('type')} - {data}")
                
                # 当收到等待中断时
                if data.get('type') == 'status' and data['data'].get('workflow_status') == 'waiting':
                    print("\n⏸️  工作流已中断")
                    
                    # 发送人工输入
                    human_input = {
                        "type": "resume",
                        "command": {
                            "action": "approved",
                            "data": {"key": "value"}
                        }
                    }
                    await ws.send(json.dumps(human_input))
                    print("✅ 人工输入已提交")
        
        except KeyboardInterrupt:
            print("\n断开连接")


# ============================================================
# 示例 7: CLI 与 Python 脚本结合
# ============================================================

import subprocess
import json

def example_cli_automation():
    """自动化脚本示例"""
    
    # 启动工作流
    print("🚀 启动工作流...")
    result = subprocess.run(
        ["python", "user_cli.py", "start"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    # 查看状态
    print("\n📊 查看状态...")
    result = subprocess.run(
        ["python", "user_cli.py", "status"],
        capture_output=True,
        text=True
    )
    print(result.stdout)


# ============================================================
# 示例 8: 处理多个中断
# ============================================================

def example_multiple_interrupts():
    """多个中断处理示例"""
    
    from user_cli import EnhancedWorkflowCLI
    
    cli = EnhancedWorkflowCLI()
    
    # 启动
    print("🚀 启动工作流...")
    cli.start_workflow()
    
    # 第一次中断
    print("\n⚠️  第一次中断...")
    command1 = cli.human_interrupt_handler()
    cli.resume_workflow(command1)
    
    # 第二次中断
    print("\n⚠️  第二次中断...")
    command2 = cli.human_interrupt_handler()
    cli.resume_workflow(command2)
    
    # 查看完整历史
    print("\n📜 查看历史...")
    cli.show_history(limit=10)


# ============================================================
# 示例 9: 配置不同的线程
# ============================================================

def example_thread_management():
    """线程管理示例"""
    
    from user_cli import EnhancedWorkflowCLI
    
    # 工作流 v1
    cli_v1 = EnhancedWorkflowCLI()
    cli_v1.thread_id = "workflow_v1"
    cli_v1.show_status()
    
    # 工作流 v2
    cli_v2 = EnhancedWorkflowCLI()
    cli_v2.thread_id = "workflow_v2"
    cli_v2.show_status()


# ============================================================
# 示例 10: 完整工作流示例
# ============================================================

def example_complete_workflow():
    """完整工作流处理示例"""
    
    import requests
    import json
    
    BASE_URL = "http://localhost:8000/api"
    
    # 步骤 1: 获取状态
    print("步骤 1: 获取初始状态")
    response = requests.get(f"{BASE_URL}/status")
    status = response.json()
    print(f"状态: {status['workflow_status']}")
    
    # 步骤 2: 启动工作流
    print("\n步骤 2: 启动工作流")
    response = requests.post(f"{BASE_URL}/start")
    print(f"结果: {response.json()['status']}")
    
    # 步骤 3: 轮询等待中断
    print("\n步骤 3: 等待中断...")
    max_attempts = 30
    attempts = 0
    while attempts < max_attempts:
        response = requests.get(f"{BASE_URL}/status")
        status = response.json()
        
        if status['workflow_status'] == 'waiting':
            print(f"✅ 已中断在 {status['next_node']}")
            break
        
        print(f"⏳ 状态: {status['workflow_status']}")
        asyncio.sleep(1)
        attempts += 1
    
    # 步骤 4: 提交人工输入
    print("\n步骤 4: 提交人工输入")
    human_data = {
        "decision": "approved",
        "modified_fields": {
            "key1": "new_value1"
        }
    }
    response = requests.post(
        f"{BASE_URL}/human_input",
        json={
            "data": human_data,
            "action": "manual_input"
        }
    )
    print(f"提交结果: {response.json()['status']}")
    
    # 步骤 5: 等待完成
    print("\n步骤 5: 等待工作流完成...")
    while True:
        response = requests.get(f"{BASE_URL}/status")
        status = response.json()
        
        if status['workflow_status'] == 'completed':
            print("🎉 工作流已完成!")
            break
        
        print(f"⏳ 状态: {status['workflow_status']}")
        asyncio.sleep(1)


if __name__ == "__main__":
    print("""
    ============================================================
    工作流管理系统 - 使用示例
    ============================================================
    
    可用的示例函数:
    
    1. example_rest_api()           # REST API 调用示例
    2. example_websocket()          # WebSocket 异步通信
    3. example_cli_automation()     # CLI 自动化脚本
    4. example_multiple_interrupts() # 多个中断处理
    5. example_thread_management()  # 线程管理
    6. example_complete_workflow()  # 完整工作流
    
    快速启动:
    
    WEB UI 模式:
        python run.py server
    
    CLI 模式:
        python run.py cli              # 菜单
        python run.py cli quick        # 快速启动
    
    ============================================================
    """)
