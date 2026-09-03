"""Build L4a convergence workorder for the failing draft pages."""
import sys, os, json
sys.path.insert(0, r"C:/Users/howie/Desktop/MyProject/MakeWiki.skills/src")
from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.verification.l4_cross_language import pair_blocks_by_section_id, _scan_blocks

DRAFTS = r"C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/.makewiki-artifacts/12-drafts"

def load(rel, lang):
    p = os.path.join(DRAFTS, lang, rel + ".md")
    if not os.path.exists(p):
        return None
    return open(p, encoding="utf-8").read()

def build(pages):
    wo = {}
    for rel in pages:
        en = load(rel, "en")
        zh = load(rel, "zh-CN")
        if en is None or zh is None:
            wo[rel] = {"error": "missing language file", "en": en is not None, "zh": zh is not None}
            continue
        docs = {"en": [], "zh-CN": []}
        for lang, content in (("en", en), ("zh-CN", zh)):
            docs[lang].append(DocumentArtifact(
                filename=rel + (".md" if lang == "en" else ".zh-CN.md"),
                base_name=rel, language_code=lang, content=content))
        paired = pair_blocks_by_section_id(docs)
        en_only, zh_only, diverged = [], [], []
        for (doc, sec, bid), lr in sorted(paired.items()):
            present = set(lr)
            if len(present) < 2:
                if "en" in present:
                    en_only.append([sec, bid])
                else:
                    zh_only.append([sec, bid])
            else:
                hashes = {l: lr[l].content_hash for l in present}
                if len(set(hashes.values())) > 1:
                    diverged.append([sec, bid])
        wo[rel] = {"en_only": en_only, "zh_only": zh_only, "diverged": diverged}
    return wo

if __name__ == "__main__":
    pages = [l.strip() for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    out = sys.argv[2]
    wo = build(pages)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(wo, f, indent=1, ensure_ascii=False)
    total = sum(len(v.get("en_only", [])) + len(v.get("zh_only", [])) + len(v.get("diverged", [])) for v in wo.values() if "error" not in v)
    for rel, v in wo.items():
        if "error" in v:
            print(rel, "ERROR", v)
        else:
            print(f"{rel}: en_only={len(v['en_only'])} zh_only={len(v['zh_only'])} diverged={len(v['diverged'])}")
    print("TOTAL ITEMS:", total, "->", out)
