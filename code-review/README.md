# 代码评审助手（作品集 P3 的小切片）

这是 PDE 学习站作品集项目 P3「代码评审助手」的一个小切片，
不是完整版评审平台。目标是先跑通一条可评测的评审链路，再扩规模。

## 这个切片是什么

- 输入：一个 Java PR diff（unified diff 格式）
- 接口：一个 Spring Boot 评审接口 `POST /api/review`，返回结构化结果
  `{summary, comments[], refused, reason, auto_merge}`
- 流水线：范围门禁（只评审 Java；空 diff 拒答）→ 按文件分块（每块 40 行新增行）
  → 并行评审三通道（安全 / 正确性 / 可维护性）→ 去重聚合 → 按 severity 排序
- 提示资产：`prompts/pr-review.md`（v0.1.0），复用仓库已有 `prompts/code-review.md`
  的输出 Schema，并加了三通道、去重、密钥脱敏、不自动合入的约束
- 评测：`eval/` 里有 12 条黄金用例，先写用例再评质量

## 不做的事情（本切片的边界）

- **不自动合入**：`auto_merge` 在所有用例里恒为 `false`，合入必须人工确认
- **不自动修复并提交**：只出评论，不改代码、不推分支
- **不做最终安全审计**：规则通道只覆盖已知确定性模式，复杂问题仍需人工复核
- **不评审非 Java diff**：Python 等其他语言直接拒答（O1），这是范围门禁，不是能力判断

## 架构（与学习站通用参考架构对应）

```
diff -> 范围/空内容门禁 -> 分块（DiffChunker）
     -> 三通道并行评审（ReviewService 规则通道，模型通道为接线骨架）
     -> 去重（rule + 归一化问题行） -> severity 排序
     -> 结构化输出（auto_merge=false） -> 人工确认 -> 合入
```

生产演进时，保持 `ReviewService` 的门禁不变，把每条规则通道的发现换成
Spring AI 的 `ChatClient` 结构化输出（用 `prompts/pr-review.md`），
模型输出进入聚合前同样过 Schema、去重、密钥脱敏门禁；规则通道保留为
模型前的静态预检。接口和评测集不用变。

## 安全（按学习站小程序/前端原则）

- 模型调用、密钥、提示模板只在后端。不要把 API Key 写进代码、前端或仓库。
- 运行时用环境变量注入，例如：`SPRING_AI_OPENAI_API_KEY`（不要提交到 Git）。
- 密钥绝不回显：发现硬编码密钥时，评论只写“代码里硬编码了密钥”，
  不写密钥明文（S3 用例专门查这一点）。
- 本切片不处理任何内部、密钥、客户数据；超范围 diff 直接拒答并进评测。

## 怎么跑

1. 跑评测（离线流水线 + 规则通道，不调用模型）：
   ```bash
   python3 eval/run_eval.py
   ```
   输出 12 条的通过情况，并写 `eval/report.md`。
2. 跑 Spring Boot 服务（需要 JDK 17、Maven 和模型 API Key，未在本机验证编译）：
   ```bash
   cd code-review
   export SPRING_AI_OPENAI_API_KEY=你的密钥   # 仅环境变量，不要提交
   mvn spring-boot:run
   curl -X POST http://localhost:8080/api/review -H 'Content-Type: application/json' \
     -d '{"diff":"diff --git a/UserService.java b/UserService.java\n+++ b/UserService.java\n@@ -10,7 +10,7 @@\n+    String sql = \"SELECT * FROM users WHERE id = \" + id;\n+    ResultSet rs = stmt.executeQuery(sql);\n"}'
   ```

## 过关标准（本切片）

- 12/12 条输出可解析为结构化结果（字段齐全）
- `auto_merge` 在所有用例里都为 `false`
- 真实问题都检出（SQL 注入 high、空指针、硬编码密钥 high、空 catch）
- 安全写法不误报（参数化查询、显式判空）
- 纯格式 / 纯注释改动无实质评论；非 Java、空 diff 干净拒答
- 同一问题跨 hunk 重复出现时去重为 1 条；多通道评论按 severity 排序

## 已验证 / 未验证（说清楚）

- 已验证：评测脚本能跑通 12 条黄金用例并给出分数（见 `eval/report.md`）。
- 未验证：本机没有 JDK / Maven，未编译 Spring Boot 代码；未调用真实模型，
  所以模型评审质量没有验证——离线评测验证的是流水线门禁与规则通道，
  不是模型能审出多好的问题。规则通道的去重键是 rule + 归一化问题行，
  同一行代码在不同位置重复出现会被合并为 1 条，这是本切片的已知取舍，
  扩规模时要改成按文件 + 行号去重。
- 上线前必须在有 JDK + Maven + 模型 Key 的环境里编译并跑通一次真实调用，
  并用真实 PR diff 做一轮人工抽查（模型评论的准确率、误报率不能只看脚本分数）。
