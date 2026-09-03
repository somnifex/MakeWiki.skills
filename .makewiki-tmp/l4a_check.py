"""L4a check over the assembled wiki tree (makewiki/), matching how documents are loaded elsewhere."""
import sys
from pathlib import Path

sys.path.insert(0, r"C:/Users/howie/Desktop/MyProject/MakeWiki.skills/src")

from makewiki_skills.verification.l4_cross_language import L4CrossLanguageVerifier
from makewiki_skills.model.document_artifact import DocumentArtifact
from collections import Counter

root = Path("C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/makewiki")

docs = {}
for lang in ["en", "zh-CN"]:
    lst = []
    for p in sorted(root.rglob("*.md")):
        if p.name.endswith(".zh-CN.md"):
            dl = "zh-CN"
        else:
            dl = "en"
        if dl != lang:
            continue
        rel = p.relative_to(root)
        name = rel.name
        if dl == "zh-CN":
            base = name[: -len(".zh-CN.md")]
        else:
            base = name[: -len(".md")]
        doc_id = (str(rel.parent / base).replace("\\", "/"))
        content = p.read_text(encoding="utf-8")
        lst.append(
            DocumentArtifact(
                filename=rel.as_posix(),
                base_name=doc_id,
                language_code=dl,
                content=content,
            )
        )
    docs[lang] = lst

ver = L4CrossLanguageVerifier()
rep = ver.verify_documents(docs)
print("L4a layer:", rep.layer, rep.name)
print(Counter(c.status for c in rep.checks))
failed = [c for c in rep.checks if c.status not in ("passed",)]
print("failed count:", len(failed))
by_target = Counter()
for c in failed:
    tgt = c.target or ""
    tgt = tgt.split(":")[0]
    by_target[tgt] += 1
for tgt, n in by_target.most_common(30):
    print(f"  {n:4d}  {tgt}")
