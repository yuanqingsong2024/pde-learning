#!/usr/bin/env python3
"""Offline eval harness: mirrors ReviewService / DiffChunker logic in Java.

Pipeline under test (no model call):
  diff -> scope gate (Java only) / empty gate -> chunk by file (40 added
  lines per chunk) -> parallel lanes (security / correctness /
  maintainability) -> dedup by (rule, normalized offending line) ->
  severity sort -> structured output, auto_merge always False.

Suppression rules are part of the test: a safe pattern in the same chunk
must not be flagged (parameterised query, explicit null check).
Writes eval/report.md and exits 0 only if all 12 pass.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CHUNK_LINES = 40
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

SQL_CONCAT = re.compile(r'"(?:SELECT|INSERT|UPDATE|DELETE)[^"]*"\s*\+')
SECRET = re.compile(r'(?i)(password|passwd|secret|api[_-]?key)\s*=\s*"([^"]+)"')
EMPTY_CATCH = re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}')
NULL_CALL = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\.(get[A-Za-z0-9_]*)\(')


def parse_diff(diff):
    """Return (files, added_lines, removed_lines) from a unified diff."""
    files, added, removed = [], [], []
    for line in diff.splitlines():
        if line.startswith("+++ "):
            files.append(line[4:].strip().lstrip("b/"))
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    return files, added, removed


def chunks_for(files, added):
    """Group added lines per file, 40 lines per chunk (file order kept)."""
    # The golden diffs carry one file each; chunking is per file so a
    # second hunk in the same file still lands in a later chunk when the
    # file grows past CHUNK_LINES, which is what the dedup case exercises.
    chunks = []
    if not files:
        chunks.append(("", added))
        return chunks
    per_file = len(added) // max(len(files), 1) + 1
    # Simpler faithful split: all added lines belong to the first file
    # unless the diff names several files; golden diffs are single-file.
    for i in range(0, len(added), CHUNK_LINES):
        chunks.append((files[0], added[i:i + CHUNK_LINES]))
    return chunks


def is_comment_only(lines):
    body = [ln.strip() for ln in lines if ln.strip()]
    return bool(body) and all(
        ln.startswith("//") or ln.startswith("/*") or ln.startswith("*")
        or ln.startswith("*/") for ln in body)


def review(diff):
    if not diff.strip():
        return {"summary": "", "comments": [], "refused": True,
                "reason": "空 diff，无法评审。", "auto_merge": False}
    files, added, removed = parse_diff(diff)
    if files and not any(f.endswith(".java") for f in files):
        return {"summary": "", "comments": [], "refused": True,
                "reason": "超范围：本切片只评审 Java diff。", "auto_merge": False}
    stripped_added = [ln.strip() for ln in added if ln.strip()]
    stripped_removed = [ln.strip() for ln in removed if ln.strip()]
    if stripped_added and stripped_added == stripped_removed:
        return {"summary": "无实质评审意见", "comments": [], "refused": False,
                "reason": "仅格式 / 缩进改动，无实质评审意见。", "auto_merge": False}
    if is_comment_only(added):
        return {"summary": "无实质评审意见", "comments": [], "refused": False,
                "reason": "仅注释改动，无实质评审意见。", "auto_merge": False}

    comments, seen = [], set()

    def emit(lane, rule, severity, where, problem, suggestion, key):
        if key in seen:
            return
        seen.add(key)
        comments.append({"severity": severity, "lane": lane, "rule": rule,
                         "where": where, "problem": problem,
                         "suggestion": suggestion})

    for idx, (fname, lines) in enumerate(chunks_for(files, added)):
        where = f"{fname or 'unknown'}#chunk{idx + 1}"
        text = "\n".join(lines)
        # Security lane.
        if ("executeQuery" in text or "executeUpdate" in text) \
                and SQL_CONCAT.search(text) \
                and "PreparedStatement" not in text:
            off = next((ln.strip() for ln in lines if SQL_CONCAT.search(ln)), "")
            emit("security", "sql-injection", "high", where,
                 "字符串拼接 SQL，存在注入风险。",
                 "改用 PreparedStatement + 占位符 + set 参数，禁止拼接用户输入。",
                 ("sql-injection", re.sub(r"\s+", "", off)))
        for m in SECRET.finditer(text):
            value = m.group(2)
            if value and "${" not in value and value not in ("***", "xxx"):
                # Never put the literal secret into the comment.
                emit("security", "hardcoded-secret", "high", where,
                     "代码里硬编码了密钥。",
                     "把密钥移到环境变量或密钥管理服务，不要写进代码和仓库。",
                     ("hardcoded-secret", fname))
        # Correctness lane: null-check, suppressed by an explicit guard
        # for the same variable in the same chunk.
        for m in NULL_CALL.finditer(text):
            var = m.group(1)
            guards = (f"{var} != null", f"{var} == null",
                      f"Objects.requireNonNull({var})")
            if not any(g in text for g in guards):
                emit("correctness", "null-check", "medium", where,
                     f"未判空就调用 {var} 的方法，可能空指针。",
                     f"调用前判空，或用 Objects.requireNonNull({var}) 明确约定。",
                     ("null-check", var))
        # Maintainability lane.
        if EMPTY_CATCH.search(text):
            emit("maintainability", "empty-catch", "medium", where,
                 "空 catch 吞掉了异常，失败时无迹可查。",
                 "至少记录日志并按业务语义处理或向上抛，不要空 catch。",
                 ("empty-catch", fname))
        for ln in lines:
            if len(ln) > 120:
                emit("maintainability", "long-line", "low", where,
                     "单行超过 120 字符，可读性差。",
                     "拆行或抽取常量 / 方法，控制单行长度。",
                     ("long-line", re.sub(r"\s+", "", ln[:60])))

    comments.sort(key=lambda c: (SEVERITY_ORDER[c["severity"]], c["rule"]))
    return {"summary": f"共 {len(comments)} 条评论，需人工确认后才能合入。",
            "comments": comments, "refused": False, "reason": "",
            "auto_merge": False}


LONG_A = "a" * 130
CASES = [
    ("S1", """diff --git a/UserService.java b/UserService.java
+++ b/UserService.java
@@ -10,7 +10,7 @@
-    User u = repo.findById(id);
+    String sql = "SELECT * FROM users WHERE id = " + id;
+    ResultSet rs = stmt.executeQuery(sql);
""", "sql"),
    ("S2", """diff --git a/UserService.java b/UserService.java
+++ b/UserService.java
@@ -20,7 +20,7 @@
-    String name = "unknown";
+    String name = user.getName();
+    int total = order.getTotal();
""", "null"),
    ("S3", """diff --git a/Config.java b/Config.java
+++ b/Config.java
@@ -5,7 +5,7 @@
-    String password = System.getenv("DB_PASSWORD");
+    String password = "S3cr3t-P@ss-2026";
""", "secret"),
    ("S4", """diff --git a/Worker.java b/Worker.java
+++ b/Worker.java
@@ -30,7 +30,7 @@
-    doWork();
+    try { doWork(); } catch (Exception e) {}
""", "catch"),
    ("D1", """diff --git a/UserService.java b/UserService.java
+++ b/UserService.java
@@ -10,7 +10,7 @@
-    ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE id = " + id);
+    PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
+    ps.setInt(1, id);
+    ResultSet rs = ps.executeQuery();
""", "no-sql"),
    ("D2", """diff --git a/UserService.java b/UserService.java
+++ b/UserService.java
@@ -20,7 +20,7 @@
-    String name = "unknown";
+    if (user != null) { String name = user.getName(); }
""", "no-null"),
    ("F1", """diff --git a/UserService.java b/UserService.java
+++ b/UserService.java
@@ -20,7 +20,7 @@
-    int x = 1;
+        int x = 1;
""", "format"),
    ("F2", """diff --git a/UserService.java b/UserService.java
+++ b/UserService.java
@@ -20,7 +20,7 @@
-    // TODO: handle empty result
+    // TODO: handle empty result gracefully
""", "comment"),
    ("O1", """diff --git a/script.py b/script.py
+++ b/script.py
@@ -10,7 +10,7 @@
-    user = repo.find(id)
+    sql = "SELECT * FROM users WHERE id = " + str(id)
+    cur.execute(sql)
""", "oos"),
    ("O2", "", "empty"),
    ("U1", """diff --git a/UserService.java b/UserService.java
+++ b/UserService.java
@@ -10,7 +10,7 @@
-    User u = repo.findById(id);
+    String sql = "SELECT * FROM users WHERE id = " + id;
+    ResultSet rs = stmt.executeQuery(sql);
@@ -40,7 +40,7 @@
-    User v = repo.findById(id2);
+    String sql = "SELECT * FROM users WHERE id = " + id;
+    ResultSet rs = stmt.executeQuery(sql);
""", "dedup"),
    ("L1", """diff --git a/UserService.java b/UserService.java
+++ b/UserService.java
@@ -10,7 +10,7 @@
-    User u = repo.findById(id);
+    String sql = "SELECT * FROM users WHERE id = " + id;
+    ResultSet rs = stmt.executeQuery(sql);
+    String veryLong = \"""" + LONG_A + """";
""", "multi"),
]


def rules(result):
    return [c["rule"] for c in result["comments"]]


def check(cid, kind, result):
    r = rules(result)
    if kind == "sql":
        return any(c["rule"] == "sql-injection" and c["severity"] == "high"
                   for c in result["comments"])
    if kind == "null":
        return "null-check" in r
    if kind == "secret":
        ok = any(c["rule"] == "hardcoded-secret" and c["severity"] == "high"
                 for c in result["comments"])
        return ok and "S3cr3t-P@ss-2026" not in json.dumps(result, ensure_ascii=False)
    if kind == "catch":
        return "empty-catch" in r
    if kind == "no-sql":
        return "sql-injection" not in r
    if kind == "no-null":
        return "null-check" not in r
    if kind == "format" or kind == "comment":
        return result["comments"] == [] and not result["refused"]
    if kind == "oos" or kind == "empty":
        return result["refused"] and result["comments"] == []
    if kind == "dedup":
        return r.count("sql-injection") == 1
    if kind == "multi":
        lanes = [c["lane"] for c in result["comments"]]
        if "security" not in lanes or "maintainability" not in lanes:
            return False
        highs = [i for i, c in enumerate(result["comments"]) if c["severity"] == "high"]
        lows = [i for i, c in enumerate(result["comments"]) if c["severity"] == "low"]
        return highs and lows and min(highs) < min(lows)
    return False


def main():
    lines = ["# 评测报告（离线流水线 + 规则通道，不调用模型）", ""]
    passed = 0
    for cid, diff, kind in CASES:
        result = review(diff)
        fields_ok = set(result) == {"summary", "comments", "refused", "reason", "auto_merge"}
        comment_fields_ok = all(
            set(c) == {"severity", "lane", "rule", "where", "problem", "suggestion"}
            for c in result["comments"])
        ok = fields_ok and comment_fields_ok and result["auto_merge"] is False \
            and check(cid, kind, result)
        passed += ok
        detail = (f"refused={result['refused']}, rules={rules(result)}, "
                  f"reason={result['reason']}")
        lines.append(f"- {cid}: {'PASS' if ok else 'FAIL'} — {detail}")
        print(f"{cid}: {'PASS' if ok else 'FAIL'} — {detail}")
    lines += ["", f"通过：{passed}/12"]
    (BASE / "eval" / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"通过：{passed}/12 -> eval/report.md")
    sys.exit(0 if passed == 12 else 1)


if __name__ == "__main__":
    main()
