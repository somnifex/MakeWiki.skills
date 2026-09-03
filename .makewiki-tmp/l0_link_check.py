"""Check L0 link validity over the assembled wiki (doc-relative resolution).

For each internal link [text](target) in each .md file (excluding
site_presentation.yaml), resolve target against the document's directory.
Print broken ones grouped by document. Also report --fix mode which rewrites
links to correct depth (adding ../ or removing ../ based on document depth).
"""
import os, re, sys

WIKI = r"C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/makewiki"
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

def iter_docs():
    for root, dirs, files in os.walk(WIKI):
        for fn in files:
            if fn.endswith(".md"):
                yield os.path.join(root, fn)

def check():
    broken_total = 0
    for path in sorted(iter_docs()):
        rel = os.path.relpath(path, WIKI).replace("\\", "/")
        content = open(path, encoding="utf-8").read()
        base = os.path.dirname(path)
        for i, line in enumerate(content.splitlines(), 1):
            for m in LINK.finditer(line):
                target = m.group(2)
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                resolved = os.path.normpath(os.path.join(base, target))
                if not os.path.exists(resolved):
                    broken_total += 1
                    print(f"BROKEN {rel}:{i} -> {target}")
    print("total broken:", broken_total)
    return broken_total

if __name__ == "__main__":
    sys.exit(1 if check() else 0)
