"""Extract pending L3/L4b/L5 review_item_ids from a verify-docs JSON report."""
import json, sys

path = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else None

data = json.load(open(path, encoding="utf-8"))
items = data["report"]["review_items"]
by_layer = {}
for it in items:
    if it["status"] == "pending":
        by_layer.setdefault(it["layer"], []).append(it["review_item_id"])

for layer, ids in sorted(by_layer.items()):
    print(f"{layer}: {len(ids)} pending")

if out:
    with open(out, "w", encoding="utf-8") as f:
        json.dump(by_layer, f, indent=1, ensure_ascii=False)
    print("written ->", out)
    with open(out.replace(".json", "_L4b_ids.txt"), "w", encoding="utf-8") as f:
        for i in by_layer.get("L4b", []):
            f.write(i + "\n")
    with open(out.replace(".json", "_L5_ids.txt"), "w", encoding="utf-8") as f:
        for i in by_layer.get("L5", []):
            f.write(i + "\n")
