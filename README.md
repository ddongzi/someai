# 一个 Code Team.

基于 LangGraph 的多 Agent 协作开发系统.

![workflow](art/workflow.png)

---

## Quickstart
### 1. 后端

```shell
uv sync
python user_server.py
```

### 2. thread前端

```shell
cd thread_webui
npm install
npm run dev
```

![thread ui](<thread_webui/截图 2026-07-14 21-00-27.png>)

---

## 任务清单
- [ ] `todo_tasks.json`将原来的task策略 迁移到 现在`tasks.md`
- [x] **上下文消息去重**：历史消息中工具调用结果重复出现（如多次 `read_file` 返回相同内容），导致token和节点调用次数过多 。
  - 方案 1：工具内检查文件 hash，若无变化则提示 Agent 使用记忆；
  - 方案 2：对历史消息做"除旧"——写入文件后，将之前同类工具的旧结果标记为空。
- [ ] **Recursion Limit**：要配置合适的limit参数,来控制节点调用次数.当前配置为100,够第一个spec_subgraph运行.
- [ ] **文件权限**：llm常常会能力越界,修改查看不必要的文件, 现在`file_ledger`不够。
- [ ] **子图检查点支持**：全图将子图视为单个节点，无法展示子图内部的详细执行步骤, 无法从子图内某个检查点进行time-travel.
- [ ] 尽量使用英文prompt, message. 节省token
- [x] **Prompt Playground**：提示词工程.引入可视化测试环境，复现和优化. 也可以用于llm单独的测试.
- [x] **LLM 过度更新文件**：通过 prompt 约束为"仅在必要时更新文件"。
- [x] 引入 SpecKit 规范驱动开发流程，生成 `constitution → spec → plan → tasks`。

---

## Issue
- [ ] 上下文消息去重中.文件写入后，之前 `read_file` 产生的 ToolMessage 内容被置空。DeepSeek 缓存机制下，内容变更会导致额外一次重新缓存。

---

## 项目结构说明

```
someai/
├── workflow.py              # 主工作流 
├── user_server.py           # FastAPI 服务端
├── thread.py                # Thread 封装：启动/继续/回放/分叉/清空
├── ready_node.py            # 就绪确认节点
├── human_node.py            # Human-in-the-Loop：审批、修改设计、时间旅行
├── issue_manager.py         # Issue 分发管理
├── utils.py                 # 通用工具函数
│
│
├── graphs/                  # 子图
│   ├── spec_graph.py        #   SpecKit 流水线：constitution→spec→plan→tasks
│   ├── coder_graph.py       #   编码 Agent：Router→Writer→Tools 循环
│   ├── test_coder_graph.py  #   测试编码 Agent
│   ├── qa_graph.py          #   质量审查 Agent
│   ├── judge_graph.py       #   评判 Agent
│   └── test_exec_graph.py   #   测试执行 Agent
│
├── tools/                   # Agent 工具集
│   ├── filer.py             #   文件读写
│   ├── rag.py               #   知识库：Milvus + BGE-M3 混合检索
│   ├── pyright_check.py     #   静态检查
│   ├── environment.py       #   环境状态（git status、依赖引用）
│   └── ...
│
├── globals/                 # 全局配置与状态
│   ├── state.py             #   GraphState / Issue / FileSnapshot 类型
│   ├── llm.py               #   LLM 客户端（DeepSeek Chat）、流式调用、用量追踪
│   └── config.py            #   全局配置
│
├── prompts/                 # 提示词
│
├── templates/               # SpecKit copied
│
├── knowledges/              # 知识库源文件
│
├── art/                     # 架构图与流程图
│
├── thread_webui/            # React 前端（线程管理 UI）
│
├── generated/               # Agent 生成代码的输出目录
│
├── .specify/               # 自定义speckit  prompt和模板
└── todo_tasks.json
```

---

## License

MIT