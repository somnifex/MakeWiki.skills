# Documentation Delivery & Verification Report

## Summary

- **Project**: `{project_name}`
- **Census & Traits**: `{repo_traits}` ({subagents_deployed} subagents, mode: `{host_mode}`)
- **Languages Generated**: `{languages}`
- **Total Pages**: `{total_pages}`

---

## Verification Results

| Check Item                | Status   | Details                                                                          |
| ------------------------- | -------- | -------------------------------------------------------------------------------- |
| **Codebase Truth**        | ✅ Passed | All `{commands_verified}` commands and `{configs_verified}` config keys grounded |
| **Cross-Language Parity** | ✅ 100%   | 0 missing sections or drifted command blocks                                     |
| **Link Integrity**        | ✅ Passed | 0 broken markdown links                                                          |
| **Anti-AI Cliché**        | ✅ Clean  | 0 banned phrases detected                                                        |

---

## Artifacts

- **Markdown Docs**: `makewiki/`
- **Offline Static Website**: `makewiki/site/index.html`
- **Exports**: `makewiki/export/`
- **Sync Bundles**: `makewiki/sync/`