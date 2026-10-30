#!/usr/bin/env python3
"""Ingest the repo's own docs into data/chunks.json (offline, no model call).

Sources (relative to the repo root, i.e. rag-doc-qa/..):
  prompts/*.md, docs/*.md, eval/*.md, README.md, index.html
Splitting: one chunk per markdown heading section, or per <h2> section in
index.html. Chunk id: "<relative-path>#<heading>".
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent.parent / "data" / "chunks.json"
MD_SOURCES = sorted(ROOT.glob("prompts/*.md")) + sorted(ROOT.glob("docs/*.md")) \
    + sorted(ROOT.glob("eval/*.md")) + [ROOT / "README.md"]


def split_md_sections(text):
    sections = []
    heading, buf = "(intro)", []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if buf and "".join(buf).strip():
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = m.group(2).strip(), []
        else:
            buf.append(line)
    if buf and "".join(buf).strip():
        sections.append((heading, "\n".join(buf).strip()))
    return sections


def clean_html(text):
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def split_html_sections(text):
    # Split on h2 and h3 so no single chunk swallows a whole page section.
    parts = re.split(r"<h[23][^>]*>(.*?)</h[23]>", text, flags=re.S)
    # parts: [before-first-heading, heading-1, body-1, heading-2, body-2, ...]
    sections = []
    for i in range(1, len(parts) - 1, 2):
        heading = clean_html(parts[i])
        body = clean_html(parts[i + 1])
        if heading and len(body) >= 20:
            sections.append((heading, body))
    return sections


def main():
    chunks = []

    def add(rel, heading, body):
        if len(body) >= 20:
            chunks.append({
                "id": f"{rel}#{heading}",
                "source": rel,
                "heading": heading,
                "text": body[:2000],
            })

    for path in MD_SOURCES:
        rel = str(path.relative_to(ROOT))
        for heading, body in split_md_sections(path.read_text(encoding="utf-8")):
            add(rel, heading, body[:1000])
    index = ROOT / "index.html"
    index_text = index.read_text(encoding="utf-8")
    # Do not drop the intro: the first h1 + lead paragraph live before the
    # first h2, and they carry the "PDE is not partial differential equations"
    # statement that the E1 golden case depends on.
    intro = clean_html(re.split(r"<h2", index_text, maxsplit=1)[0])
    add("index.html", "(intro)", intro)
    for heading, body in split_html_sections(index_text):
        add("index.html", heading, body)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(chunks)} chunks -> {OUT}")


if __name__ == "__main__":
    main()
