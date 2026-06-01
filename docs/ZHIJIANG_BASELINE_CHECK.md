# 智匠系统基线验收清单

## 启动验收

- [ ] 项目能通过 `start.bat` 或 `sh start.sh` 启动。
- [ ] 浏览器访问 `http://127.0.0.1:5000` 正常打开。
- [ ] 前端页面标题显示“智匠系统”。
- [ ] 前端副标题显示“基于 RAG 的智能工艺规划与知识检索工作台”。

## 前端验收

- [ ] 首页包含工艺需求输入区。
- [ ] 首页包含工艺知识检索结果区。
- [ ] 首页包含工艺方案生成区。
- [ ] 首页包含方案评估区。
- [ ] 首页包含专家审核区。
- [ ] 生成按钮显示“生成工艺方案”。
- [ ] 输入框 placeholder 使用工艺需求示例。

## 后端能力验收

- [ ] 原知识库接口不被破坏。
- [ ] 原文本检索能力保留。
- [ ] 原 LLM 生成链路保留。
- [ ] FAISS 向量召回能力保留。
- [ ] BM25 / RRF 融合排序能力保留。
- [ ] text2vec-base-chinese 本地向量模型路径配置保留。
- [ ] 日志与诊断能力保留。

## PR1 工业模式入口验收

- [ ] `/api/chat` 不传 `mode` 时默认走原 ARPM `role_chat` 链路。
- [ ] `/api/chat` 传入 `mode=process_planning` 时进入智匠工业模式入口。
- [ ] 智匠前端请求携带 `mode=process_planning`。
- [ ] 工业模式返回兼容前端现有字段的占位响应。
- [ ] 工业模式不进入角色对话、角色记忆、角色一致性或 RAG 生成链路。
- [ ] 后端日志可区分 `mode=role_chat` 与 `mode=process_planning`。
- [ ] 后端日志包含 `process_entry_enabled=true` 和后续模块 pending 状态。

## PR2 工艺需求结构化解析验收

- [ ] 新增 `backend/core/process_parser.py`，并可被直接 import。
- [ ] `mode=process_planning` 返回 `requirement_vector`。
- [ ] 示例输入能解析出 `material=铝合金`、`batch=小批量`、`feature=薄壁件`、`process_type=数控铣削`、`quality=高精度`、`equipment=三轴数控铣床`。
- [ ] 未解析字段返回 `unknown`，并写入 `missing_fields`。
- [ ] 空输入或 `None` 输入不会导致解析模块崩溃。
- [ ] `role_chat` 默认链路不调用工艺解析模块。
- [ ] 后端日志包含 `requirement_parser_enabled=true`、`raw_query`、`requirement_vector` 和 `missing_fields`。
- [ ] 本 PR 不实现工艺查询增强、ProcessRetriever、ProcessSim、CAD/PDF/图像处理、方案评分或专家审核闭环。

## PR3 工艺查询增强验收

- [ ] 新增 `backend/core/process_query_enhancer.py`，并可被直接 import。
- [ ] `mode=process_planning` 返回 `enhanced_query`。
- [ ] `enhanced_query.process_query` 包含 `[行业=机械加工]` 和 `[任务=工艺规划]`。
- [ ] 示例输入能在 `process_query` 中生成 `[材料=铝合金]`、`[批量=小批量]`、`[结构特征=薄壁件]`、`[设备资源=三轴数控铣床]`、`[质量要求=高精度]`、`[工艺类型=数控铣削]`。
- [ ] `unknown` 字段以明确标签形式稳定保留，不导致请求失败。
- [ ] `process_query` 不包含角色扮演、角色设定、ARPM 等旧定位字段。
- [ ] `role_chat` 默认链路不调用工艺查询增强模块。
- [ ] 本 PR 不实现 ProcessRetriever、ProcessSim、CAD/PDF/图像处理、方案评分或专家审核闭环。

## 本次不验收

- [ ] 不实现 CAD 解析。
- [ ] 不实现图像检索。
- [ ] 不实现图纸识别。
- [ ] 不实现 PDF 深度解析。
- [ ] 不实现 ProcessSim。
- [ ] 不实现工艺评分功能。
- [ ] 不实现专家审核闭环。
