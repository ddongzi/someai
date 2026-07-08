import os
import json
import subprocess
import threading
import queue
import time
from pathlib import Path
class PyrightLspTool:
    def __init__(self, project_root_path: str):
        self.project_root = os.path.abspath(project_root_path)
        # 将本地路径转换为 LSP 标准的 URI 格式
        self.root_uri = Path(self.project_root).as_uri()
        
        self.process = None
        self.msg_id = 1
        self.response_buffers = {}  # 存储不同 id 的响应队列
        self.lock = threading.Lock()
        
        self._start_server()

    def _start_server(self):
        """启动 Pyright 并开启异步读取线程"""
        self.process = subprocess.Popen(
            ["pyright-langserver", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # 启动后台线程，防止标准输出缓冲区被异步日志堵满导致死锁
        threading.Thread(target=self._read_loop, daemon=True).start()
        self._initialize()

    def _read_loop(self):
        """持续读取 LSP 输出，分发消息"""
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line or not line.startswith("Content-Length:"):
                    continue
                
                length = int(line.split(":")[1].strip())
                self.process.stdout.readline()  # 跳过 \r\n
                content = self.process.stdout.read(length)
                
                msg = json.loads(content)
                if "id" in msg:
                    # 如果是带 id 的响应，放入对应的队列中
                    msg_id = msg["id"]
                    with self.lock:
                        if msg_id not in self.response_buffers:
                            self.response_buffers[msg_id] = queue.Queue()
                        self.response_buffers[msg_id].put(msg)
                else:
                    # 异步通知（如日志、诊断信息），Agent 暂时忽略
                    pass
        except Exception as e:
            print(f"LSP 读取线程异常: {e}")

    def _send_message(self, method: str, params: dict, is_notification=False):
        """发送 JSON-RPC 消息"""
        current_id = None
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        if not is_notification:
            with self.lock:
                current_id = self.msg_id
                self.msg_id += 1
            payload["id"] = current_id

        body = json.dumps(payload)
        message = f"Content-Length: {len(body)}\r\n\r\n{body}"
        self.process.stdin.write(message)
        self.process.stdin.flush()
        return current_id

    def _wait_for_response(self, msg_id: int, timeout=5.0):
        """线程安全地等待指定 id 的响应"""
        with self.lock:
            if msg_id not in self.response_buffers:
                self.response_buffers[msg_id] = queue.Queue()
            q = self.response_buffers[msg_id]
        
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return {"error": {"message": f"请求超时 {timeout}s"}}

    def _initialize(self):
        """标准的 LSP 初始化双向握手"""
        # 1. 发送 initialize
        init_id = self._send_message("initialize", {
            "processId": os.getpid(),
            "rootUri": self.root_uri,
            "capabilities": {
                "textDocument": {
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True}
                }
            }
        })
        self._wait_for_response(init_id)
        
        # 2. 发送 initialized 通知（没有 id），激活服务器
        self._send_message("initialized", {}, is_notification=True)
        time.sleep(1) # 给 Pyright 一点扫描索引项目的时间

    def open_file_in_lsp(self, file_path: str, content: str):
        """告诉 LSP 服务器当前文件已被打开（同步代码内容）"""
        abs_path = os.path.abspath(file_path)
        file_uri = Path(abs_path).as_uri()
        self._send_message("textDocument/didOpen", {
            "textDocument": {
                "uri": file_uri,
                "languageId": "python",
                "version": 1,
                "text": content
            }
        }, is_notification=True)

    def find_definition(self, file_path: str, line: int, character: int):
        """
        查找定义 (Go to Definition)
        :param line: 从 0 开始的行号
        :param character: 从 0 开始的字符列号
        """
        abs_path = os.path.abspath(file_path)
        file_uri = Path(abs_path).as_uri()
        
        req_id = self._send_message("textDocument/definition", {
            "textDocument": {"uri": file_uri},
            "position": {"line": line, "character": character}
        })
        return self._wait_for_response(req_id)

    def find_references(self, file_path: str, line: int, character: int):
        """查找所有引用 (Find References)"""
        abs_path = os.path.abspath(file_path)
        file_uri = Path(abs_path).as_uri()
        
        req_id = self._send_message("textDocument/references", {
            "textDocument": {"uri": file_uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": True} # 包含声明本身
        })
        return self._wait_for_response(req_id)

    def close(self):
        """关闭服务"""
        if self.process:
            self.process.terminate()

import os
from typing import Optional, Any
from langchain_core.tools import tool

# 1. 初始化一个全局的单例占位符
_lsp_client: Optional[PyrightLspTool] = None

def get_lsp_client(project_root: str = "./generated") -> PyrightLspTool:
    """获取或初始化全局的 LSP 客户端单例"""
    global _lsp_client
    if _lsp_client is None:
        # 当 Agent 第一次需要使用代码分析时，懒加载启动进程
        _lsp_client = PyrightLspTool(project_root_path=project_root)
    return _lsp_client


# 2. 封装“查找定义”工具
@tool
def find_symbol_definition(
    file_path: str, 
    line: int, 
    character: int, 
    project_root: str = "."
) -> str:
    """
    跳转到指定符号的定义位置（Go to Definition）。
    当你想知道某个类、函数或变量是在哪里实现的，请调用此工具。
    
    参数:
        file_path: 目标文件相对于项目根目录或绝对路径。
        line: 符号所在的行号，注意：必须从 0 开始计数（即第 1 行输入 0）。
        character: 符号所在的字符列号，注意：必须从 0 开始计数（即第 1 个字符输入 0）。
        project_root: 项目的根目录路径，用于初始化基础服务。
    返回:
        JSON 字符串，包含定义所在的文件 URI、起始和结束的行列范围。
    """
    try:
        lsp = get_lsp_client(project_root)
        
        # 稳妥起见，查询前最好先同步一次文件状态，避免未保存的代码导致位置错乱
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lsp.open_file_in_lsp(file_path, f.read())
                
        response = lsp.find_definition(file_path, line, character)
        
        # 格式化输出，方便 LLM 快速捕捉关键路径
        if "result" in response and response["result"]:
            import json
            return json.dumps(response["result"], indent=2, ensure_ascii=False)
        elif "error" in response:
            return f"LSP 服务错误: {response['error']['message']}"
        else:
            return "未找到该符号的定义位置，请确认行列号（从0开始）是否精准对齐了符号名称。"
    except Exception as e:
        return f"执行跳转定义失败，错误原因: {str(e)}"


# 3. 封装“查找引用”工具
@tool
def find_symbol_references(
    file_path: str, 
    line: int, 
    character: int, 
    project_root: str = "."
) -> str:
    """
    查找指定符号在整个项目中的所有引用和调用位置（Find References）。
    当你想重构某个函数、修改某个类、或者确认这个变量在哪些文件里被使用过时，请调用此工具。
    
    参数:
        file_path: 目标文件相对于项目根目录或绝对路径。
        line: 符号所在的行号，注意：必须从 0 开始计数。
        character: 符号所在的字符列号，注意：必须从 0 开始计数。
        project_root: 项目的根目录路径。
    返回:
        JSON 字符串，包含所有引用该符号的文件路径及准确的范围列表。
    """
    try:
        lsp = get_lsp_client(project_root)
        
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lsp.open_file_in_lsp(file_path, f.read())
                
        response = lsp.find_references(file_path, line, character)
        
        if "result" in response and response["result"]:
            import json
            return json.dumps(response["result"], indent=2, ensure_ascii=False)
        elif "error" in response:
            return f"LSP 服务错误: {response['error']['message']}"
        else:
            return "未在项目中找到该符号的其他引用点。"
    except Exception as e:
        return f"执行查找引用失败，错误原因: {str(e)}"
