"""Fix L0 link validity v2: rewrite internal links to L0-valid doc-relative depth.

Target normalization strategy (in order):
1. Strip leading '/', './', '../' runs and '#fragment'; strip trailing '.md'.
2. If the bare doc-id resolves to an en file at WIKI root -> use it.
3. Else if the link's document directory contains <basename>.md -> resolve to
   that same-directory file's full doc-id.
4. Else, search the wiki for a unique file whose name matches the target's
   basename; if unique, use its doc-id; else report UNRESOLVED.
Rebuild as ('../' * depth) + doc_id + '.md' + fragment.
Idempotent: skips links already in canonical form.
"""
import os, re, sys

WIKI = r"C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/makewiki"
LINK = re.compile(r"(\]\()([^)]+)(\))")

def iter_docs():
    for root, dirs, files in os.walk(WIKI):
        for fn in files:
            if fn.endswith(".md"):
                yield os.path.join(root, fn)

# Pre-compute doc-id -> rel path (en files) and basename -> [doc_ids]
ALL_DOCS = {}
for root, dirs, files in os.walk(WIKI):
    for fn in files:
        if fn.endswith(".md"):
            full = os.path.join(root, fn)
            rel = os.path.relpath(path := full, WIKI).replace("\\", "/")
            if rel.endswith(".zh-CN.md"):
                continue
            ALL_DOCS[rel[:-len(".md")]] = rel

BASENAME_INDEX = {}
for doc_id in ALL_DOCS:
    BASENAME_INDEX.setdefault(doc_id.rsplit("/", 1)[-1], []).append(doc_id)

def normalize(target):
    frag = ""
    t = target
    if "#" in t:
        t, frag = t.split("#", 1)
        frag = "#" + frag
    t = t.replace("/MakeWiki/", "/").replace("/MakeWiki", "/")
    t = t.lstrip("./")
    if t.endswith(".md"):
        t = t[:-len(".md")]
    return t, frag

def resolve(doc_id, doc_rel, target):
    # 0. doc-relative filesystem resolution first: the link may already point
    #    at a real file from the document's own directory (e.g.
    #    ./../manage/tokens.md from reference/api/x.md is reference/manage/tokens).
    doc_dir = doc_rel.rsplit("/", 1)[0] if "/" in doc_rel else ""
    stripped = target.split("#", 1)[0]
    if stripped.lower().endswith(".md"):
        fs = os.path.normpath(os.path.join(WIKI, doc_dir, stripped))
        if os.path.exists(fs) and os.path.isfile(fs):
            rel_resolved = os.path.relpath(fs, WIKI).replace("\\", "/")
            if rel_resolved.endswith(".zh-CN.md"):
                rel_resolved = rel_resolved[: -len(".zh-CN.md")]
            else:
                rel_resolved = rel_resolved[: -len(".md")]
            return rel_resolved
    # 1. wiki-root doc-id
    if doc_id in ALL_DOCS:
        return doc_id
    # 2. same-directory file
    bare = doc_id.rsplit("/", 1)[-1]
    same_dir = (doc_dir + "/" + bare) if doc_dir else bare
    if same_dir in ALL_DOCS:
        return same_dir
    # 3. unique basename match
    cands = BASENAME_INDEX.get(bare)
    if cands and len(cands) == 1:
        return cands[0]
    return None

def main(apply):
    rewritten = 0
    unresolved = 0
    for path in sorted(iter_docs()):
        rel = os.path.relpath(path, WIKI).replace("\\", "/")
        content = open(path, encoding="utf-8").read()
        depth = rel.count("/")
        prefix = "../" * depth
        changed = False
        out_lines = []
        for line in content.splitlines():
            def repl(m):
                nonlocal rewritten, unresolved, changed
                pre, target, post = m.group(1), m.group(2), m.group(3)
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    return m.group(0)
                doc_id, frag = normalize(target)
                if not doc_id:
                    return m.group(0)
                resolved = resolve(doc_id, rel, target)
                if resolved is None:
                    unresolved += 1
                    print(f"UNRESOLVED {rel}: {target}")
                    return m.group(0)
                new_target = prefix + resolved + ".md" + frag
                if new_target != target:
                    rewritten += 1
                    changed = True
                    return pre + new_target + post
                return m.group(0)
            out_lines.append(LINK.sub(repl, line))
        if changed:
            open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out_lines) + "\n")
    print(f"rewritten links: {rewritten}; unresolved: {unresolved}; apply={apply}")

if __name__ == "__main__":
    main(apply=("--apply" in sys.argv))
