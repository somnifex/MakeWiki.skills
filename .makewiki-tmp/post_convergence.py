"""Post-convergence pipeline steps:
  assemble  - rebuild flat makewiki/ tree from drafts
  linkfix   - rewrite internal links to L0-valid doc-relative depth (on WIKI)
  linkcheck - verify L0 doc-relative link validity (broken count must be 0)
  l4a       - full L4a recheck over all 32 draft pages
  l5scan    - duplicate L5 command-text scan over the assembled tree

Authoritative order: assemble -> linkfix -> linkcheck -> l5scan -> (audits).
"""
import os, sys, subprocess, shutil

sys.path.insert(0, r"C:/Users/howie/Desktop/MyProject/MakeWiki.skills/src")

ART = r"C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/.makewiki-artifacts"
SRC_EN = os.path.join(ART, "12-drafts", "en")
SRC_ZH = os.path.join(ART, "12-drafts", "zh-CN")
WIKI = r"C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/makewiki"
TMP = r"C:/Users/howie/Desktop/MyProject/MakeWiki.skills/.makewiki-tmp"

step = sys.argv[1] if len(sys.argv) > 1 else "all"

if step in ("all", "assemble"):
    if os.path.exists(WIKI):
        shutil.rmtree(WIKI)
    os.makedirs(WIKI)

    def copy_tree(src_dir, suffix):
        n = 0
        for root, dirs, files in os.walk(src_dir):
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                src = os.path.join(root, fn)
                rel = os.path.relpath(src, src_dir).replace("\\", "/")
                base = rel[:-3]
                dst = os.path.join(WIKI, base + suffix)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
                n += 1
        return n

    en_n = copy_tree(SRC_EN, ".md")
    zh_n = copy_tree(SRC_ZH, ".zh-CN.md")
    plan = os.path.join(ART, "15-site-presentation-plan", "site_presentation.yaml")
    shutil.copyfile(plan, os.path.join(WIKI, "site_presentation.yaml"))
    print(f"[assemble] en={en_n} zh={zh_n} + site_presentation.yaml -> {WIKI}")

if step in ("all", "linkfix"):
    r = subprocess.run(
        [sys.executable, os.path.join(TMP, "l0_link_fix.py"), "--apply"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print("[linkfix]", (r.stdout.strip() or r.stderr.strip()).splitlines()[-1])

if step in ("all", "linkcheck"):
    r = subprocess.run(
        [sys.executable, os.path.join(TMP, "l0_link_check.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = r.stdout + r.stderr
    total = [l for l in out.splitlines() if l.startswith("total broken:")]
    print("[linkcheck]", total[-1] if total else out.strip()[:200])
    sys.exit(1 if any(l.startswith("BROKEN") for l in out.splitlines()) else 0)

if step in ("all", "l4a"):
    pages = [l.strip() for l in open("/tmp/draft_pages.txt", encoding="utf-8") if l.strip()]
    args = [p + ".md" for p in pages]
    r = subprocess.run(
        [sys.executable, "/tmp/recheck_page.py"] + args,
        cwd=r"C:/Users/howie/Desktop/MyProject/MakeWiki.skills",
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = r.stdout + r.stderr
    fails = [l for l in out.splitlines() if l.startswith("[FAIL]")]
    passes = [l for l in out.splitlines() if l.startswith("[PASS]")]
    print(f"[l4a] PASS={len(passes)} FAIL={len(fails)}")
    for l in fails:
        print(l)
    sys.exit(1 if fails else 0)

if step in ("all", "l5scan"):
    from makewiki_skills.toolkit.markdown_tools import MarkdownTool
    from pathlib import Path
    import collections
    md = MarkdownTool()
    root = Path(WIKI)
    problems = 0
    for p in sorted(root.rglob("*.md")):
        rel = p.relative_to(root).as_posix()
        content = p.read_text(encoding="utf-8")
        facts = md.extract_facts(content, "zh-CN" if "zh" in rel else "en", rel)
        c = collections.Counter(cmd.strip() for cmd in facts.commands)
        dup = {k: v for k, v in c.items() if v > 1}
        if dup:
            problems += 1
            print("=== " + rel + " ===")
            for k, v in dup.items():
                print("    " + repr(k) + " -> " + str(v))
    print("[l5scan] docs with duplicate command texts:", problems)
    sys.exit(1 if problems else 0)
