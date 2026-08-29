# Example: makewiki-review

```bash
# Review English and Chinese versions (L0-L5 + Quality Gate)
/makewiki-review --lang en --lang zh-CN

# Run unified verification + Quality Gate via toolkit
python scripts/run_toolkit.py verify-docs . --lang en --lang zh-CN
# Exit code: 0 PASS, 1 FAIL
```