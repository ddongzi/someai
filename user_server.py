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
import os
from globals.llm import LLM_TOKEN_LOGS_PATH
 
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

    async def init_knowledge_background():
        """后台异步初始化知识库，不阻塞服务器启动"""
        global knowledge
        try:
            knowledge = get_knowledge()
            run_logger.info("🎉 全局知识库 KnowledgeManager 初始化成功！")
        except Exception as e:
            run_logger.error(f"❌ 知识库初始化失败: {e}")
            knowledge = None

    asyncio.create_task(init_knowledge_background())

    async with my_workflow.setup() as active_saver:
        yield

    run_logger.info("服务器关闭")


app = FastAPI(title="Thread thread", lifespan=lifespan)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils import json_serializer

# 允许 React 开发服务器的端口访问
origins = [
    "*",
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


@app.get("/api/stat/")
async def get_llm_stats():
    """
    读取本地 llm_token_logs.jsonl 文件，返回所有大模型的历史用量统计
    """
    # 检查文件是否存在，防止服务崩溃
    if not os.path.exists(LLM_TOKEN_LOGS_PATH):
        return []  # 如果还没有日志，直接返回空列表

    stats_list = []
    
    try:
        # 打开并逐行读取 jsonl 文件
        with open(LLM_TOKEN_LOGS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # 跳过空行
                
                # 将单行字符串反序列化为 Python 字典
                log_data = json.loads(line)
                stats_list.append(log_data)
                
    except json.JSONDecodeError as e:
        # 如果文件不幸损坏，抛出 500 错误或记录日志
        raise HTTPException(status_code=500, detail=f"日志文件格式损坏: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")

    # 默认返回最新调用的记录在最前面（逆序）
    # 如果想按时间正序，把 .reverse() 删掉即可
    stats_list.reverse() 
    
    return stats_list



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