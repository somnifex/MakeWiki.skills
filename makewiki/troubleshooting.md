# Troubleshooting

## `Error: Target directory does not exist`

**Symptom:** Running `/makewiki` or any other MakeWiki command shows:

```
Error: Target directory does not exist: <path>
```

**Cause:** The path passed to the command does not point to a valid directory.

**Solution:** Make sure you are running the command from within a Claude Code conversation that is open in a valid project directory. If you specified a path explicitly, check that it exists and is a directory.

## `Language '<code>' not registered, skipping`

**Symptom:** After running `/makewiki`, one or more requested languages are skipped with this warning.

**Cause:** The requested language code does not have a built-in profile. Built-in codes are: `en`, `zh-CN`, `ja`, `de`, `fr`.

**Solution:** Use one of the built-in language codes. If you need a language that isn't built in, you can add a profile by creating a new file under `src/makewiki_skills/languages/profiles/` following the pattern of existing profiles.

## `Wiki directory not found`

**Symptom:** Running `/makewiki-review` or `/makewiki-validate` shows:

```
Error: Wiki directory not found: <path>
```

**Cause:** The command expects a `makewiki/` directory (or the directory specified in `output_dir`) to already exist with generated documentation.

**Solution:** Run `/makewiki` first to generate the documentation. If you've already generated docs to a custom directory, specify the correct path:

```text
/makewiki-validate ./custom-output-dir
```

## `NOT_FOUND` from toolkit bootstrap

**Symptom:** The skill prints `NOT_FOUND` during startup and falls back to manual mode.

**Cause:** The bootstrap script could not prepare the home-scoped toolkit environment under `~/.makewiki`. This is usually caused by permission errors or locked files from a previous run.

**Solution:** Delete the `~/.makewiki` directory and re-run the command:

```bash
rm -rf ~/.makewiki
```

The skill will recreate the toolkit environment on the next run. If the problem persists, the skill continues in manual mode without the toolkit — documentation generation still works.

## `uv run pytest` fails

**Symptom:** Tests fail after a fresh install.

**Cause:** Dependencies may not be fully installed, or you may be using a Python version older than 3.11.

**Solution:**

1. Check your Python version: `python --version` (must be 3.11+)
2. Re-sync dependencies: `uv sync`
3. Re-run tests: `uv run pytest`

## Cross-language review shows critical issues

**Symptom:** `/makewiki-review` reports critical issues with a low consistency score.

**Cause:** One or more language versions are missing commands, config keys, or file paths that appear in other versions. This can happen when generated code blocks differ between languages.

**Solution:** Re-run `/makewiki` to regenerate all language versions from the same evidence. If the issue persists, check the inconsistency table to identify specific mismatches and fix the affected pages.

## Validation reports broken links

**Symptom:** `/makewiki-validate` reports broken internal links.

**Cause:** A generated page references another page that doesn't exist in the output directory — for example, a link to `configuration.zh-CN.md` when Chinese wasn't generated.

**Solution:** Ensure all languages referenced in links were included in the generation. Re-run `/makewiki` with the correct `--lang` flags, or fix the links manually.
