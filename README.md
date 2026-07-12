# 一个code team.

```shell
python user_server.py
```

```shell
cd thread_webui
npm run dev
```

## 节点
### 0712
- file工具不够，需要一个检查信息工具， 文件是否完整，行数，就是缩略工具。而非完全readfile ，token 过大
- 不合理。AIMessage(content='文件已存在，我需要使用 `apply_search_replace` 来更新它。由于文件内容非常长，我将用 SEARCH/REPLACE 替换整个文件内容。',

频繁调用工具，llm一直在找知识，确保自己有足够知识。 虽然很正常，不断反思，确定自己做的

test prompt却一直在写app

工具应该支持 list 参数 或者union ,尽可能.

inspect project 不应该存在. 我们不应该过度依赖于 工具, 这个完全可以通过state为支持. cuowu . llm不能直接调用state, 要么我们传入message, 要么tool

应该为各个角色分配文件权限,  角色应该知道自己用那些文件

改善后, 基本上会调用三次知识库,是合理的.

现在看起来都是合理的.越小越好
1. 我们的需求不够精,
2. prompt职责不够严格

现在就是 因为 从需求检索知识库, 得到很多内容,  这侧面就增大了  广度, 会导致llm 进行更多操作.
recrusion limit 就是一个prompt 不超过多少条.
必须严格要求相似度和topk
RRFRanker策略 下面: 稀疏向量很容易完虐稠密向量, 导致排名后, 稠密向量是none

### 0710
现在状态：
- prompt不优，导致llm思维宽广，频繁调用工具，在coder/testcoder 子图出不来。这违背了角色分明：比如不应该git提交。
- 工具不够明确广泛：如llm总想全部更新，比起我给了ast工具。这导致会产生大量token.可能还会强行调取不那么匹配的工具
- api调取很快，比如我们遇到循环了，就会导致token飙升，最多内置25次循环。这目前会消耗大约0.2元

## 技术思路：
1. prompt管理：使用yaml+模板解析，能够为一个角色节点配置多场景。
2. 模型和token：
   1. 本地测试开发流程验证通过ollama，但是`qwen 2.5coder -1.5B`这样模型，调用tool参数是不合理的，不可采用。
   2. openrouter免费模型的限制完全不足以支撑频繁调用。
   3. token节省，使用langchain的SQLite Cache缓解一些. 
3. 快速开发验证：使用thread的checkpoint，thread需要前端webui才灵活。设置了 重放/分叉/继续操作，能够节省token,也能更快调试开发。

## 技术扩展：
- 定量评价：1. token，  2. 多模型对比生成

## 迭代过程的问题：
Q1. 在涉及多轮对话时候，历史消息需要组织吗？
   目前仍然是messages字段，一味的增加。
   这可能涉及到Transfromer框架的注意力机制，对不同Message
Q2. 知识库与state的边界？
   比如PROD,SPEC是否放在state更快更广泛。 但是知识库更加精准。

## 一些理念：
1. 人机边界和协同。
- llm发散，会很喜欢调用工具，这使得在初期要跟着llm的ToolMessage请求补充我们的工具。至少对新项目来说，人决策、模型执行是模糊的。
- PRD需求稳定, SPEC接口/数据边界 都应该由human完全控制，DD技术文档由模型，他有着更好的经验技术。
- 因为文档可能过大，human规划控制todo_tasks，每次执行只实现一个小功能
