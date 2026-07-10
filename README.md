# 一个code team.

## 节点
### 0710
现在状态：
- prompt不优，导致llm思维宽广，频繁调用工具，在coder/testcoder 子图出不来。这违背了角色分明：比如不应该git提交。
- 工具不够明确广泛：如llm总想全部更新，比起我给了ast工具。这导致会产生大量token.可能还会强行调取不那么匹配的工具

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

## 终极期待：
- godot西部世界