"""Move <!-- makewiki:section=X --> markers to immediately before the H2 they
belong to (zh drafts put the marker AFTER the H2, blank line separated), and
drop blank lines between a marker and its following H2.

Transformation per file:
- A marker line whose preceding non-blank line is a heading (`#...`) is moved
  to just BEFORE that heading line.
- A marker followed by blank line(s) then a heading has the blanks dropped.
Idempotent. Applies to both en and zh-CN drafts.
"""
import io, os, re

ART = r"C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/.makewiki-artifacts/12-drafts"
MARKER = re.compile(r"^\s*<!--\s*makewiki:section=([A-Za-z0-9_.\-]+)\s*-->\s*$")
HEADING = re.compile(r"^#{1,6}\s+")

def fix_lines(lines):
    out = list(lines)
    changed = False
    # Pass 1: move marker above a heading that precedes it
    i = 0
    while i < len(out):
        if MARKER.match(out[i]):
            # find previous non-blank
            k = len(out) - 1
            # search backwards
            j = i - 1
            while j >= 0 and out[j].strip() == "":
                j -= 1
            if j >= 0 and HEADING.match(out[j]) and out[j].lstrip().startswith("##"):
                # move marker before that heading (the heading may be preceded
                # by other markers; insert directly before the heading line)
                marker_line = out.pop(i)
                # after pop, heading is at index j (unchanged since j < i)
                out.insert(j, marker_line)
                changed = True
                # do not advance i; re-examine same index (now heading)
                continue
        i += 1
    # Pass 2: remove blank lines between marker and following heading
    res = []
    i = 0
    while i < len(out):
        line = out[i]
        res.append(line)
        if MARKER.match(line):
            j = i + 1
            blanks = 0
            while j < len(out) and out[j].strip() == "":
                blanks += 1
                j += 1
            if blanks and j < len(out) and out[j].lstrip().startswith("#"):
                changed = True
                i = j - 1
        i += 1
    return res, changed

def fix_dir(base, suffix):
    n = 0
    for root, dirs, files in os.walk(base):
        for fn in files:
            if not fn.endswith(suffix):
                continue
            p = os.path.join(root, fn)
            s = io.open(p, encoding="utf-8").read()
            lines = s.split("\n")
            new_lines, changed = fix_lines(lines)
            if changed:
                io.open(p, "w", encoding="utf-8", newline="").write("\n".join(new_lines))
                n += 1
    return n

en = fix_dir(os.path.join(ART, "en"), ".md")
zh = fix_dir(os.path.join(ART, "zh-CN"), ".md")
print(f"fixed files: en={en} zh={zh}")
