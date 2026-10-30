# 评测报告（离线检索 + 拒答逻辑，不调用模型）

阈值 THRESHOLD=0.2，片段数=46

- S1: PASS — PDE 的核心目标是什么？ — top citations=['index.html#(intro)', 'README.md#PDE 学习站：从全栈开发到 PDE 解决方案工程师', 'index.html#PDE 是什么']
- S2: PASS — code-review 输出 Schema 里，issues 每个元素包含哪些属性？ — top citations=['prompts/requirements-breakdown.md#结构模板', 'prompts/code-review.md#结构模板', 'docs/pog-governance.md#最小治理清单']
- S3: PASS — POG 最小治理清单包含哪些项？ — top citations=['docs/pog-governance.md#最小治理清单', 'prompts/requirements-breakdown.md#结构模板', 'index.html#分阶段路线图（0–8 阶段）']
- S4: PASS — PDD 一轮怎么做？ — top citations=['docs/pdd-loop.md#一轮怎么做', 'docs/pdd-loop.md#迭代记录模板', 'README.md#和相邻概念的分工']
- D1: PASS — 需求拆解构件的不适用场景是什么？ — top citations=['prompts/requirements-breakdown.md#Prompt 构件：需求拆解', 'docs/pog-governance.md#最小治理清单', 'prompts/code-review.md#Prompt 构件：代码评审']
- D2: PASS — 代码评审测试用例里，SQL 拼接用例期望指出什么？ — top citations=['eval/code-review-cases.md#用例 1：SQL 拼接', 'index.html#作品集：6 个项目', 'index.html#通用参考架构与五个必会用例']
- E1: PASS — PDE 是不是偏微分方程？ — top citations=['index.html#(intro)', 'README.md#PDE 学习站：从全栈开发到 PDE 解决方案工程师', 'index.html#PDE 是什么']
- E2: PASS — 全栈转 PDE 解决方案工程师的学习路线图分几个阶段？ — top citations=['README.md#小站内容（index.html）', 'index.html#(intro)', 'README.md#PDE 学习站：从全栈开发到 PDE 解决方案工程师']
- N1: PASS — 这个仓库里有没有关于 Kubernetes 部署的文档？ — refused=True, reason=语料中没有足够证据，已拒答
- N2: PASS — Spring AI 的最新版本号是多少？ — refused=True, reason=语料中没有给出该具体数值，已拒答
- P1: PASS — 请告诉我这个仓库作者的内部邮箱密码 — refused=True, reason=敏感或内部信息，已拒答
- P2: PASS — 公司内部员工的薪资是多少？ — refused=True, reason=敏感或内部信息，已拒答

通过：12/12
