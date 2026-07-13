"""FastAPI 服务器 - 替代 CLI 的工作流管理"""
from re import A
from langchain_core.load import dumpd
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
from fastapi.sse import EventSourceResponse, ServerSentEvent
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from fastapi.sse import EventSourceResponse

from langgraph.types import Command
from collections.abc import AsyncIterable, Iterable
from fastapi.responses import StreamingResponse
from globals.logger import run_logger
import asyncio
from thread import Thread
from workflow import MyWorkflow
from tools.rag import get_knowledge
from utils import get_file_logger

sse_logger = get_file_logger(
    logger_name='sse',
    log_dir='./logs',
    filename='sse.log'
)
my_workflow = MyWorkflow()
knowledge = None
thread = Thread(workflow=my_workflow)

# ============================================================
# FastAPI 应用
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_logger.info("服务器启动")
    global knowledge
    try:
        # 确保只在服务真正运转的那一刻，在单进程内部初始化一次
        knowledge = get_knowledge()
        run_logger.info("🎉 全局知识库 KnowledgeManager 初始化成功！")
    except Exception as e:
        run_logger.error(f"❌ 知识库初始化失败: {e}")
        knowledge = None
    async with my_workflow.setup() as active_saver:
        yield 
        
    run_logger.info("服务器关闭")


app = FastAPI(title="Thread thread", lifespan=lifespan)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils import json_serializer

# 允许 React 开发服务器的端口访问
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
event_queue = asyncio.Queue()


@app.get("/api/stream")
async def stream(request: Request,) :
    """SSE 监听流（GET 请求接收）"""

    # 2. 定义符合 FastAPI 标准的 SSE 异步生成器
    async def sse_event_generator():
        try:
            while True:
                # 检查客户端是否已经断开连接（如用户关闭网页），防止服务器白白运行
                if await request.is_disconnected():
                    break

                # 从队列中取出工作流吐出的事件
                event = await event_queue.get()
                
                # 收到结束信号，优雅退出流连接
                if event is None:

                    break

                # 3. 严格遵循 SSE 标准格式化： data: <content>\n\n
                # 使用 json.dumps 确保特殊字符被正确转义
                content = f"data: {json.dumps(dumpd(event))}\n\n"
                sse_logger.info(content)                
                yield content
                
                # 标记队列任务完成
                event_queue.task_done()
                
        except asyncio.CancelledError:
            # 捕捉连接取消异常
            pass

    # 4. 返回符合 text/event-stream 规范的 StreamingResponse
    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓存，确保数据实时秒发
        }
    )
# ============================================================
# REST API 端点
# ============================================================

@app.get("/api/state/")
async def get_status_endpoint():
    """获取当前工作流状态"""
    return await thread.get_state()

@app.post("/api/clear/")
async def clear_endpoint():
    """获取当前工作流状态"""
    return await thread.clear_history()

@app.post("/api/start/")
async def start_workflow_endpoint(): #
    """启动工作流"""

    asyncio.create_task(thread.start_workflow(event_queue=event_queue))  
    return {"status": "workflow_started", "message": "请前往 /api/stream 监听流"}

@app.post("/api/continue/")
async def continue_workflow():
    """继续执行工作流"""
    await thread.continue_workflow()
    return {"status": "workflow_continued", "message": "工作流继续执行中，请前往 /api/stream 监听流"}

@app.post("/api/replay/")
async def replay_workflow(body: Dict[str, Any]):
    """从指定 checkpoint 重放。"""
    checkpoint_id = body.get("checkpoint_id")
    if not checkpoint_id:
        raise HTTPException(status_code=400, detail="缺少 checkpoint_id 参数")
    
    try:
        result = await thread.replay(checkpoint_id, event_queue=event_queue)
        return {"status": "success", "message": f"已回溯到 checkpoint {checkpoint_id}", "result": result}
    except Exception as e:
        run_logger.exception(f"回溯失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/fork/")
async def fork_workflow(body: Dict[str, Any]):
    checkpoint_id = body.get("checkpoint_id")
    state = body.get("state")

    if not checkpoint_id:
        raise HTTPException(status_code=400, detail="缺少 checkpoint_id 参数")
    
    try:
        result = await thread.fork(checkpoint_id, state, event_queue=event_queue)
        return {"status": "success", "message": f"已回溯到 checkpoint {checkpoint_id}", "result": result}
    except Exception as e:
        run_logger.exception(f"回溯失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/human_input/")
async def human_input(body: Dict[str, Any]):
    """处理人工干预输入"""
    checkpoint_id = body.get("checkpoint_id")
    interrupt_id = body.get("interrupt_id")
    data = body.get("data")

    if not checkpoint_id:
        raise HTTPException(status_code=400, detail="缺少 checkpoint_id 参数")
    
    try:
        result = await thread.resume_workflow(checkpoint_id, interrupt_id, data, event_queue=event_queue)
        return {"status": "success", "message": f"已回溯到 checkpoint {checkpoint_id}", "result": result}
    except Exception as e:
        run_logger.error(f"回溯失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/api/history/")
async def get_history(limit: int = 20):
    """获取工作流历史"""
    return await thread.get_history(limit)


import subprocess
import sys
def run_server():
    """运行 FastAPI 服务器"""
    run_logger.info("🌐 启动 FastAPI 服务器，服务器地址:   http://localhost:8000")
    
    subprocess.run([
        sys.executable, 
        "-m", 
        "uvicorn", 
        "user_server:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--workers", "1"  # 👈 显式指定单进程模式，防止 Milvus 抢锁
    ])


# ============================================================
# 启动脚本
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    run_server()