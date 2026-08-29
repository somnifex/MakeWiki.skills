# Markdown Validation Rules

The validator runs structural checks only (no LLM). For full evidence
verification, run `verify-docs` (unified L0–L5 + Quality Gate) instead.

- **H1 Check**: Exactly one `# ` per markdown document.
- **Heading Order**: No skip from `#` to `###` without intermediate `##`.
- **Link Check**: Internal relative markdown links must resolve to existing files.
- **Empty Check**: Documents with under 10 non-whitespace words are marked

  empty. Pages whose LLM-populated slots (faq / troubleshooting /
  usage_examples) came back empty must still render the `UNKNOWN` marker
  rather than be silently dropped.
- **Code Block Language**: All fenced code blocks must declare a language identifier.