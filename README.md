# PDE 学习站：Prompt-Driven Engineering

> PDE（Prompt-Driven Engineering）是把 Prompt 当软件构件来做，而不是当聊天咒语来写。
>
> 核心目标：每个 Prompt（或一组 Prompt）都要**结构清楚、行为稳定、能测、能改、能复用**。

本仓库是一个面向开发者的 PDE 学习小站骨架，适合 Java / 全栈背景、想带团队落地 Prompt 资产的开发负责人。

## 和相邻概念的分工

- **Prompt Engineering**：这一次怎么写才答得好
- **PDD**：开发循环快不快（意图 → 生成 → 评估 → 迭代）
- **PDE**：这个 Prompt 本身质量够不够
- **POG**：全公司怎么管、复用、审计这些资产

## 小站怎么用

打开 `index.html`（或开启 GitHub Pages 后访问站点首页），可以：

1. 按路线图学习：概念 → 结构模板 → 质量清单 → 评估 → PDD 迭代 → POG 治理
2. 在实验场里改模板、对照质量清单自评
3. 到 `prompts/` 看可直接复用的 Prompt 构件，到 `eval/` 看对应的测试用例

## 目录结构

```text
index.html              小站首页 + 路线图 + 质量清单自评 + PDD 实验场
prompts/
  code-review.md        代码评审 Prompt 构件（带版本、输入输出 Schema、测试要点）
  requirements-breakdown.md  需求拆解 Prompt 构件
eval/
  code-review-cases.md  代码评审的测试用例与评分标准
  requirements-breakdown-cases.md  需求拆解的测试用例与评分标准
docs/
  pdd-loop.md           PDD 循环：意图 → 生成 → 评估 → 迭代
  pog-governance.md     POG 治理：目录、版本、复用、审计
java/
  src/main/java/pde/PromptTemplate.java  最小 Prompt 模板渲染示例（Java）
```

## 学习路线（建议 4 周）

- 第 1 周：把一个你常用的 Prompt 改写成结构化构件，写清输入输出
- 第 2 周：给它配 5–10 条测试用例和评分标准，跑一次回归
- 第 3 周：走三轮 PDD 迭代，记录每次改了什么、为什么改、效果如何
- 第 4 周：按 POG 规范入库：命名、版本、负责人、复用说明、审计记录

## 待办

- [ ] 把第一个真实业务 Prompt 按模板入库
- [ ] 给它配测试用例并跑通一次评估
- [ ] 在团队内评审一次，确定命名与版本规范
