# 智匠系统后续 PR 计划

## 已完成基线：前端外壳切换为智匠系统工作台

- 前端用户可见名称切换为“智匠系统”。
- README 和 docs 已切换为智匠系统定位。
- 原 ARPM 后端 RAG 检索底座保留。

## PR 1：新增工业模式后端入口

### 目标

- 支持 `/api/chat` 请求传入 `mode=process_planning`。
- 将智匠工业模式入口与原 ARPM `role_chat` 链路隔离。
- 不传 `mode` 时默认保留原 ARPM 聊天与 RAG 检索链路。
- 暂不实现工艺解析、检索增强、ProcessRetriever、ProcessSim、图纸/CAD 处理或方案评分。

### 验收

- 原 ARPM 链路不受影响。
- 智匠前端请求能进入 `process_planning` 分支。
- 后端返回兼容前端现有 schema 的占位响应。
- 日志能识别 `mode=role_chat` 与 `mode=process_planning`。

### 已接入

- `process_parser`: done in PR2

### 后续待接入

- `process_query_enhancer`: pending
- `process_retriever`: pending
- `process_scorer`: pending
- `process_evaluator`: pending

## PR 2：新增工艺需求结构化解析

### 目标

- 新增规则/关键词版 `process_parser`。
- 在 `mode=process_planning` 工业模式入口中返回 `requirement_vector`。
- 提取 `feature`、`material`、`batch`、`quality`、`equipment`、`cost_limit`、`time_limit`、`process_type`、`raw_query` 和 `missing_fields`。
- 暂不实现工艺查询增强、ProcessRetriever、ProcessSim、工艺方案生成、评分、CAD/PDF/图像识别。

### 验收

- `role_chat` 默认链路不调用工艺解析模块。
- `process_planning` 请求能返回结构化工艺需求。
- 示例“小批量铝合金薄壁件、数控铣削、高精度、三轴数控铣床”可解析出关键字段。
- 缺失字段返回 `unknown`，并进入 `missing_fields`。
- 后端日志能看到 `requirement_parser_enabled=true`、`raw_query`、`requirement_vector` 和 pending 模块状态。

PR 3：新增工艺查询增强

PR 4：新增工艺知识元数据结构

PR 5：新增 ProcessRetriever，复用原 ARPM 检索底座

PR 6：新增 ProcessSim、CaseQuality、FreshQuality

PR 7：新增工艺 Prompt 与方案生成

PR 8：新增方案评分与专家审核

PR 9：新增知识库反哺

PR 10：新增文件格式初判与图纸/CAD 上传 MVP

PR 11：新增模型父节点与视图子证据

PR 12：新增视图向量检索

PR 13：融合文本召回与图像召回
