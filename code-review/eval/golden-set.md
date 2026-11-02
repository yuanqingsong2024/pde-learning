# 黄金评测集（12 条，先写用例再评质量）

范围：一个 Java PR diff，分块 → 并行评审（安全 / 正确性 / 可维护性三通道）
→ 去重聚合 → 结构化评论，**永远不自动合入**（`auto_merge` 恒为 `false`）。
离线评测验证的是流水线门禁与规则通道，不是模型评审质量：
规则通道只覆盖已知的确定性模式，模型通道在 Java 里是接线骨架，
其输出进入聚合前必须过同样的 Schema、去重、密钥脱敏门禁。

| id | 类别 | diff 要点 | 期望 |
|----|------|-----------|------|
| S1 | 真实问题·安全 | 字符串拼接 SQL：`executeQuery("SELECT ... WHERE id = " + id)` | 有 `sql-injection` 评论，severity 为 high |
| S2 | 真实问题·正确性 | 未判空直接调用：`user.getName()`、`order.getTotal()`，无任何判空 | 有 `null-check` 评论 |
| S3 | 真实问题·安全 | 硬编码密钥：`password = "S3cr3t-P@ss-2026"` | 有 `hardcoded-secret` 评论，severity 为 high，且输出全文**不含该密钥明文** |
| S4 | 真实问题·可维护性 | 空 catch 吞异常：`catch (Exception e) {}` | 有 `empty-catch` 评论 |
| D1 | 干扰·不误报 | 参数化查询：`PreparedStatement` + `?` + `setInt` | **无** `sql-injection` 评论 |
| D2 | 干扰·不误报 | 先判空再调用：`if (user != null) { user.getName(); }` | **无** `null-check` 评论 |
| F1 | 无实质改动 | diff 只有空白 / 缩进改动 | 评论为空，`refused=false`，reason 说明无实质改动 |
| F2 | 无实质改动 | diff 只有注释改动 | 评论为空，`refused=false`，reason 说明无实质改动 |
| O1 | 超范围 | 非 Java diff：Python 文件 `script.py` | `refused=true`，评论为空，不评审 |
| O2 | 无内容 | 空 diff | `refused=true`，评论为空 |
| U1 | 去重 | 同一 SQL 拼接行在两个 hunk 里重复出现 | `sql-injection` 评论**恰好 1 条** |
| L1 | 多通道聚合 | 同一 diff 同时有 SQL 拼接和超长行（>120 字符） | 至少 1 条安全评论 + 1 条可维护性评论，且 high 在 low 之前 |

注：S3 里的密钥是合成测试值，不是真实凭证，仅用于验证评审输出不回显密钥明文。

类别说明：S=真实问题，D=干扰写法（安全写法不误报），F=无实质改动，
O=超范围 / 无内容必须拒答或忽略，U=去重，L=多通道聚合与排序。

过关标准（本切片）：
- 12/12 通过；每条输出字段齐全（`summary, comments[], refused, reason, auto_merge`）
- `auto_merge` 在所有用例里都为 `false`
- S3 输出不含密钥明文；O1、O2 干净拒答；U1 去重后恰好 1 条
