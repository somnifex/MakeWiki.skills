# Contributing to MakeWiki.skills

Thank you for your interest in contributing to **MakeWiki.skills**! We welcome community contributions of all kinds: bug fixes, new language profiles, documentation improvements, framework adapters, and architecture enhancements.

---

## 🧭 Code of Conduct & Core Principles

When contributing to MakeWiki.skills, keep these four architectural pillars in mind:
1. **Ground-Truth First**: All generated documentation facts must be traceable to real project evidence (source AST, configs, manifests, or commands).
2. **Subagent Budget Discipline**: Never spawn unbounded agents. Keep subagent allocations bounded (1 to 10 max).
3. **No AI Clichés (去 AI 腔)**: Technical writing must sound natural, concise, and professional. Avoid binary tropes ("not X but Y"), abstract buzzwords ("convergence"), and trailing colons in headings.
4. **Zero Pollution**: Tools must operate ephemerally and leave no stray files outside the designated `makewiki/` directory.

---

## 🛠️ Development Setup

MakeWiki.skills requires **Python 3.11+** and uses [`uv`](https://github.com/astral-sh/uv) as the primary package and environment manager.

```bash
# 1. Clone the repository
git clone https://github.com/somnifex/MakeWiki.skills.git
cd MakeWiki.skills

# 2. Create virtual environment and install all dependencies
uv sync --all-extras
```

---

## 🧪 Testing & Quality Standards

Every Pull Request must pass all automated tests, linting, and type checks.

### Running Tests

```bash
uv run pytest --basetemp=.pytest_temp
```

### Static Type Checking

```bash
uv run mypy src/makewiki_skills
```

### Code Formatting & Linting

```bash
uv run ruff check --fix .
uv run ruff format .
```

---

## 🌐 Adding a New Language Profile

To add support for a new language (e.g. Spanish `es` or Korean `ko`):

1. **Create Profile File**: Add `src/makewiki_skills/languages/profiles/<code_name>.py`.
2. **Define Terminology**: Map Diátaxis and Enterprise delivery terms to native technical idioms:

   ```python
   from makewiki_skills.languages.profile import LanguageProfile, TerminologyMap, FormattingRules, FormalityLevel

   PROFILE = LanguageProfile(
       code="es",
       display_name="Spanish",
       native_name="Español",
       terminology=TerminologyMap(
           installation="Instalación",
           getting_started="Primeros pasos",
           # ...
       ),
       formality=FormalityLevel.NEUTRAL,
       formatting=FormattingRules(...),
       generation_hints="...",
       file_suffix=".es",
   )
   ```
3. **Register in Registry**: Add the profile import in `src/makewiki_skills/languages/registry.py`.
4. **Add Unit Tests**: Ensure language generation and template rendering tests pass.

---

## 📦 Pull Request Process

1. Fork the repository and create your branch from `main`:

   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Write clean code with type annotations and docstrings.
3. Add corresponding unit and integration tests under `tests/`.
4. Verify that all tests pass (`uv run pytest --basetemp=.pytest_temp`).
5. Submit a Pull Request with a clear explanation of changes and motivation.

Thank you for helping build the future of AI-native documentation engineering!
