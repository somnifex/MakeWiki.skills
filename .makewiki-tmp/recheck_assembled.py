"""L4a recheck over the ASSEMBLED wiki tree (makewiki/).

Mirrors /tmp/recheck_page.py but loads from the assembled flat tree:
  <doc>.md (en) / <doc>.zh-CN.md (zh-CN)
"""
import sys, os
sys.path.insert(0, r"C:/Users/howie/Desktop/MyProject/MakeWiki.skills/src")
from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.verification.l4_cross_language import pair_blocks_by_section_id, _scan_blocks

WIKI = r"C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/makewiki"

def load(rel):
    en = os.path.join(WIKI, rel + ".md")
    zh = os.path.join(WIKI, rel + ".zh-CN.md")
    return (
        open(en, encoding="utf-8").read() if os.path.exists(en) else None,
        open(zh, encoding="utf-8").read() if os.path.exists(zh) else None,
    )

def check(pages):
    ok = True
    for rel in pages:
        en, zh = load(rel)
        docs = {"en": [], "zh-CN": []}
        for lang, content in (("en", en), ("zh-CN", zh)):
            if content is None:
                continue
            docs[lang].append(DocumentArtifact(
                filename=rel + (".md" if lang == "en" else ".zh-CN.md"),
                base_name=rel,
                language_code=lang,
                content=content))
        paired = pair_blocks_by_section_id(docs)
        haslangs = {l for l, c in docs.items() if c}
        problems = []
        for (doc, sec, bid), lr in sorted(paired.items()):
            present = set(lr)
            if len(present) < len(haslangs):
                problems.append(f"  ASYMMETRIC @{sec} [[id:{bid}]] present={sorted(present)}")
            else:
                hashes = {l: lr[l].content_hash for l in present}
                if len(set(hashes.values())) > 1:
                    problems.append(f"  DIVERGED @{sec} [[id:{bid}]]")
        for lang, content in (("en", en), ("zh-CN", zh)):
            if not content:
                continue
            for ref in _scan_blocks(content, lang):
                if ref.is_technical and not ref.block_id and not ref.exempted:
                    problems.append(f"  UNTAGGED-TECH ({lang}): {ref.full_block.splitlines()[0].strip()[:80]}")
        if problems:
            ok = False
            print(f"[FAIL] {rel}")
            for p in problems:
                print(p)
        else:
            print(f"[PASS] {rel}")
    return ok

if __name__ == "__main__":
    sys.exit(0 if check(sys.argv[1:]) else 1)
