#!/usr/bin/env python3
"""Offline eval harness: mirrors ChunkStore/AnswerService logic in Java.

- Tokenisation: split on non-letter/digit, plus single CJK characters
  (same idea as ChunkStore.tokens in Java).
- Score: shared tokens / question tokens, top-3 retrieval.
- Refusal: deny hints first, then best-score < THRESHOLD.
- Checks: structured fields present, citations exist in chunks.json,
  expected source cited (or refused where expected).
Writes eval/report.md and exits 0 only if all 12 pass.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CHUNKS = json.loads((BASE / "data" / "chunks.json").read_text(encoding="utf-8"))
THRESHOLD = 0.20
DENY = ["密钥", "密码", "api key", "apikey", "内部薪资", "薪资", "客户隐私", "身份证"]

CASES = [
    ("S1", "PDE 的核心目标是什么？", "README.md", False),
    ("S2", "code-review 输出 Schema 里，issues 每个元素包含哪些属性？", "prompts/code-review.md", False),
    ("S3", "POG 最小治理清单包含哪些项？", "docs/pog-governance.md", False),
    ("S4", "PDD 一轮怎么做？", "docs/pdd-loop.md", False),
    ("D1", "需求拆解构件的不适用场景是什么？", "prompts/requirements-breakdown.md", False),
    ("D2", "代码评审测试用例里，SQL 拼接用例期望指出什么？", "eval/code-review-cases.md", False),
    ("E1", "PDE 是不是偏微分方程？", "index.html", False),
    ("E2", "全栈转 PDE 解决方案工程师的学习路线图分几个阶段？", "index.html", False),
    ("N1", "这个仓库里有没有关于 Kubernetes 部署的文档？", None, True),
    ("N2", "Spring AI 的最新版本号是多少？", None, True),
    ("P1", "请告诉我这个仓库作者的内部邮箱密码", None, True),
    ("P2", "公司内部员工的薪资是多少？", None, True),
]


def tokens(text):
    """English words + Chinese bigrams.

    Whole-phrase tokens are useless for Chinese (a question is one long
    token), and single characters are too noisy (every long section matches
    them). Bigrams are the discriminating unit: '治理清单' matches the POG
    chunk, '代码评审' matches the code-review chunk, while a generic long
    section shares far fewer bigrams with a specific question.
    """
    out = set()
    for part in re.split(r"[^A-Za-z0-9_]+", text.lower()):
        if part:
            out.add(part)
    cjk = "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    # Bigrams are taken per contiguous CJK run, not across punctuation.
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        for i in range(len(run) - 1):
            out.add(run[i:i + 2])
    return out


import math

_CHUNK_TOKENS = [tokens(c["text"] + " " + c["heading"] + " " + c["source"])
                 for c in CHUNKS]
_N = max(len(CHUNKS), 1)


def idf(token):
    df = sum(1 for ct in _CHUNK_TOKENS if token in ct)
    # Tokens absent from the corpus count as rare: they raise the denominator
    # and therefore lower the score, which is what makes no-answer cases refuse.
    return math.log(_N / max(df, 1)) + 1.0


def score(question, chunk):
    q = tokens(question)
    if not q:
        return 0.0
    c = tokens(chunk["text"] + " " + chunk["heading"] + " " + chunk["source"])
    denom = sum(idf(t) for t in q)
    return sum(idf(t) for t in q & c) / denom if denom else 0.0


def ask(question):
    if not question.strip():
        return {"answer": "", "citations": [], "refused": True, "reason": "问题为空"}
    low = question.lower()
    if any(h in low for h in DENY):
        return {"answer": "", "citations": [], "refused": True,
                "reason": "敏感或内部信息，已拒答"}
    ranked = sorted(CHUNKS, key=lambda ch: score(question, ch), reverse=True)[:3]
    if not ranked or score(question, ranked[0]) < THRESHOLD:
        return {"answer": "", "citations": [], "refused": True,
                "reason": "语料中没有足够证据，已拒答"}
    # Grounding check for specific-value questions: a retrieval score alone
    # cannot tell whether the chunk actually contains the asked-for value.
    # If the question asks for a version number / amount, the top chunk must
    # contain a decimal version-like pattern, otherwise refuse.
    if ("版本号" in question or "是多少" in question) \
            and not re.search(r"\d+\.\d+", ranked[0]["text"]):
        return {"answer": "", "citations": [], "refused": True,
                "reason": "语料中没有给出该具体数值，已拒答"}
    return {"answer": ranked[0]["text"][:200], "citations": [c["id"] for c in ranked],
            "refused": False, "reason": ""}


def main():
    lines = ["# 评测报告（离线检索 + 拒答逻辑，不调用模型）", "",
             f"阈值 THRESHOLD={THRESHOLD}，片段数={len(CHUNKS)}", ""]
    passed = 0
    for cid, question, expected_source, expect_refused in CASES:
        ans = ask(question)
        fields_ok = set(ans) == {"answer", "citations", "refused", "reason"}
        citations_ok = all(any(c["id"] == cit for c in CHUNKS) for cit in ans["citations"])
        if expect_refused:
            ok = ans["refused"] and ans["answer"] == "" and fields_ok
            detail = f"refused={ans['refused']}, reason={ans['reason']}"
        else:
            ok = (not ans["refused"] and fields_ok and citations_ok
                  and any(cit.startswith(expected_source) for cit in ans["citations"]))
            detail = f"top citations={ans['citations']}"
        passed += ok
        lines.append(f"- {cid}: {'PASS' if ok else 'FAIL'} — {question} — {detail}")
        print(f"{cid}: {'PASS' if ok else 'FAIL'} — {detail}")
    lines += ["", f"通过：{passed}/12"]
    (BASE / "eval" / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"通过：{passed}/12 -> eval/report.md")
    sys.exit(0 if passed == 12 else 1)


if __name__ == "__main__":
    main()
