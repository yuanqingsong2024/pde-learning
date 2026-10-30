#!/usr/bin/env python3
"""Run the holdout set (eval/holdout-set.md) against the same ask() logic
as the golden set in run_eval.py. Keep the two sets separate: do not tune
thresholds on this set, and do not merge it into the golden set.

Usage: python3 eval/run_holdout.py   (from rag-doc-qa/)
Writes eval/holdout-report.md and exits 0 only if all 6 pass.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_eval as r

CASES = [
    ("H1", "代码评审构件的质量自评包含哪几项？", "prompts/code-review.md", False),
    ("H2", "需求拆解测试用例里，约束冲突的用例期望指出什么？",
     "eval/requirements-breakdown-cases.md", False),
    ("H3", "POG 治理从个人到团队再到公司是怎么演进的？",
     "docs/pog-governance.md", False),
    ("H4", "解决方案工程师的一天包含哪些环节？", "index.html", False),
    ("H5", "作品集包含哪些项目？", "index.html", False),
    ("H6", "这个仓库里有没有关于 Docker 部署的文档？", None, True),
]


def main():
    lines = ["# Holdout 评测报告（与黄金集同一套 ask() 逻辑，不调用模型）", ""]
    passed = 0
    for cid, question, expected_source, expect_refused in CASES:
        ans = r.ask(question)
        if expect_refused:
            ok = ans["refused"] and ans["answer"] == ""
            detail = f"refused={ans['refused']}, reason={ans['reason']}"
        else:
            rank = next((i + 1 for i, c in enumerate(ans["citations"])
                         if c.startswith(expected_source)), None)
            ok = (not ans["refused"] and rank is not None)
            detail = f"target rank={rank}, top={ans['citations']}"
        passed += ok
        lines.append(f"- {cid}: {'PASS' if ok else 'FAIL'} — {question} — {detail}")
        print(f"{cid}: {'PASS' if ok else 'FAIL'} — {detail}")
    lines += ["", f"通过：{passed}/{len(CASES)}"]
    (Path(__file__).resolve().parent / "holdout-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    print(f"通过：{passed}/{len(CASES)} -> eval/holdout-report.md")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()
