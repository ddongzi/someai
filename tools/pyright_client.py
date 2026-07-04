import os
import json
import subprocess
import threading
import queue
import time
from urllib.parse import urljoin, pathname2url

class PyrightLspTool:
    def __init__(self, project_root_path: str):
        self.project_root = os.path.abspath(project_root_path)
        # 将本地路径转换为 LSP 标准的 URI 格式
        self.root_uri = urljoin('file:', pathname2url(self.project_root))
        
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
        file_uri = urljoin('file:', pathname2url(abs_path))
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
        file_uri = urljoin('file:', pathname2url(abs_path))
        
        req_id = self._send_message("textDocument/definition", {
            "textDocument": {"uri": file_uri},
            "position": {"line": line, "character": character}
        })
        return self._wait_for_response(req_id)

    def find_references(self, file_path: str, line: int, character: int):
        """查找所有引用 (Find References)"""
        abs_path = os.path.abspath(file_path)
        file_uri = urljoin('file:', pathname2url(abs_path))
        
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
