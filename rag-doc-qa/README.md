# RAG 文档问答（作品集 P1 的小切片）

这是 PDE 学习站作品集项目 P1「企业文档问答（RAG）」的一个晚上能做完的小切片，
不是完整版 100 篇文档 / 50 条用例。目标是先跑通一条可评测的链路，再扩规模。

## 这个切片是什么

- 语料：本仓库已有的文档，不新增语料库——`prompts/`、`docs/`、`eval/`、`README.md`
- 接口：一个 Spring Boot 查询接口 `POST /api/qa`，返回结构化答案
  `{answer, citations[], refused, reason}`
- 生成：提示模板在 `prompts/qa-answer.md`，只允许用引用片段回答，证据不足就拒答
- 评测：`eval/` 里有 12 条黄金用例，先写用例再评质量

## 架构（与学习站通用参考架构对应）

```
问题 -> 权限/越权守门 -> 关键词检索（本切片的检索实现，见 ChunkStore）
     -> 证据校验（引用必须指向真实片段） -> 结构化输出
     -> refused=true 时不编造，直接说明原因
```

生产演进时，把 `ChunkStore` 的关键词检索换成向量检索 + 混合检索 + 重排，
把 `AnswerService` 里模板化的答案合成换成 Spring AI 的 `ChatClient` 结构化输出，
接口和评测集不用变。Spring AI 的接线见 `RagDocQaApplication` 里的注释。

## 安全（按学习站小程序/前端原则）

- 模型调用、密钥、提示模板只在后端。不要把 API Key 写进代码、前端或仓库。
- 运行时用环境变量注入，例如：`SPRING_AI_OPENAI_API_KEY`（不要提交到 Git）。
- 本切片不处理任何内部、密钥、客户数据；越权/超范围问题直接拒答并进评测。

## 怎么跑

1. 生成片段库（离线，不调用模型）：
   ```bash
   python3 tools/ingest.py
   ```
   生成 `data/chunks.json`，每条有 `id`（`源文件#标题`）、`source`、`heading`、`text`。
2. 跑评测（离线检索 + 拒答逻辑，不调用模型）：
   ```bash
   python3 eval/run_eval.py
   ```
   输出 12 条的通过情况，并写 `eval/report.md`。
3. 跑 Spring Boot 服务（需要 JDK 17、Maven 和模型 API Key，未在本机验证编译）：
   ```bash
   cd rag-doc-qa
   export SPRING_AI_OPENAI_API_KEY=你的密钥   # 仅环境变量，不要提交
   mvn spring-boot:run
   curl -X POST http://localhost:8080/api/qa -H 'Content-Type: application/json' \
     -d '{"question":"PDE 的核心目标是什么？"}'
   ```

## 过关标准（本切片）

- 12/12 条输出可解析为结构化答案（字段齐全）
- 引用全部指向 `data/chunks.json` 里真实存在的片段 id
- 2 条无答案用例都干净拒答（`refused=true`，不编造答案）
- 只有达到这三条，才向 100 篇文档 / 50 条用例的完整版扩规模

注意：阈值（0.20）和具体数值证据检查是在这 12 条上校准的，S2、E2 的目标
片段目前是前 3 名引用中的第 2 名，不是第 1 名。扩规模前需要留出未见过的
用例做验证，并考虑加 reranking，不能只看这 12 条的分数。

## 已验证 / 未验证（说清楚）

- 已验证：摄入脚本能从仓库文档生成片段库；评测脚本能跑通 12 条黄金用例并给出分数
  （见 `eval/report.md`，含通过数与失败原因）。
- 未验证：本机没有 JDK / Maven，未编译 Spring Boot 代码；未调用真实模型，
  所以 Spring AI 生成一步是接线骨架，答案合成在离线评测里用检索片段模板化呈现。
  上线前必须在有 JDK + Maven + 模型 Key 的环境里编译并跑通一次真实调用。
