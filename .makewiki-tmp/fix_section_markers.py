"""Remove blank lines between <!-- makewiki:section=X --> markers and the
heading that follows them, so the section parser (which requires the marker to
be IMMEDIATELY followed by a heading) accepts the document.

Applies to both en and zh-CN drafts. Idempotent.
"""
import io, os, re

ART = r"C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/.makewiki-artifacts/12-drafts"
MARKER = re.compile(r"^\s*<!--\s*makewiki:section=([A-Za-z0-9_.\-]+)\s*-->\s*$")

def fix_dir(base, suffix):
    n = 0
    for root, dirs, files in os.walk(base):
        for fn in files:
            if not fn.endswith(suffix):
                continue
            p = os.path.join(root, fn)
            s = io.open(p, encoding="utf-8").read()
            lines = s.split("\n")
            out = []
            i = 0
            changed = False
            while i < len(lines):
                line = lines[i]
                out.append(line)
                if MARKER.match(line):
                    # swallow blank lines between marker and next heading
                    j = i + 1
                    blanks = 0
                    while j < len(lines) and lines[j].strip() == "":
                        blanks += 1
                        j += 1
                    if blanks and j < len(lines) and lines[j].lstrip().startswith("#"):
                        changed = True
                        i = j - 1  # keep the heading; drop the blanks
                    # else keep blanks (marker followed by prose = orphan case; leave)
                i += 1
            if changed:
                io.open(p, "w", encoding="utf-8", newline="").write("\n".join(out))
                n += 1
    return n

en = fix_dir(os.path.join(ART, "en"), ".md")
zh = fix_dir(os.path.join(ART, "zh-CN"), ".md")
print(f"fixed files: en={en} zh={zh}")
