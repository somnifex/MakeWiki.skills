"""Real-browser functional tests for the compiled static site (Playwright).

The compiled site is a single-file offline SPA. These tests open it in a real
Chromium via ``file://`` and exercise the client behaviour that no unit test
can: routing (document routes vs in-page anchors), search on/off, theme
persistence, language switching, mobile drawer navigation, the on-page table of
contents, code copy, and broken-link robustness.

The tests skip gracefully when Playwright or a Chromium browser is not
installed, so headless CI without browsers stays green.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from makewiki_skills.model.site_presentation import (
    SiteNavItem,
    SitePresentationPlan,
    SiteVisualPreferences,
)
from makewiki_skills.renderer.site_compiler import SiteCompiler

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_site(tmp_path: Path, *, include_search: bool = True) -> Path:
    """Build a small bilingual wiki and return the path to index.html."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()

    (wiki / "README.md").write_text(
        "# Sample Project\n\nWelcome to the sample project.\n\n"
        "## Architecture\n\nHere is the architecture.\n\n"
        "## Deploy\n\nDeployment notes.\n\n"
        + "\n\nAdditional prose.\n" * 40
        + "## Closing\n\nThe end of the page.\n",
        encoding="utf-8",
    )
    (wiki / "README.zh-CN.md").write_text(
        "# 示例项目\n\n欢迎使用示例项目。\n\n## 架构\n\n这里是架构。\n",
        encoding="utf-8",
    )
    (wiki / "getting-started.md").write_text(
        "# Quick Start\n\nRun `npm install`.\n\n"
        "## Install\n\n```bash\nnpm install\n```\n\n"
        "### Verifying\n\nRun `npm test`.\n",
        encoding="utf-8",
    )
    (wiki / "getting-started.zh-CN.md").write_text(
        "# 快速起步\n\n运行 `npm install`。\n",
        encoding="utf-8",
    )
    (wiki / "config.md").write_text(
        "# Configuration\n\n| Key | Value |\n|---|---|\n| port | 8080 |\n\n"
        "See [Overview](../README.md) and [Quick Start](getting-started.md#install).\n",
        encoding="utf-8",
    )

    plan = SitePresentationPlan(
        project_title="Sample Project",
        project_description="A sample project.",
        navigation=[
            SiteNavItem(
                document_id="README",
                route="/",
                title="Home",
                titles={"zh-CN": "首页"},
                nav_group="Overview",
                ordering=10,
            ),
            SiteNavItem(
                document_id="getting-started",
                route="/getting-started",
                title="Quick Start",
                titles={"zh-CN": "快速起步"},
                nav_group="Getting Started",
                ordering=20,
            ),
            SiteNavItem(
                document_id="config",
                route="/config",
                title="Configuration",
                nav_group="Reference",
                ordering=30,
            ),
        ],
        languages=["en", "zh-CN"],
        default_language="en",
        visual=SiteVisualPreferences(
            theme="auto",
            include_search=include_search,
            accent_color="#2563eb",
            brand_label="MW",
        ),
    )

    written = SiteCompiler(plan=plan).compile(wiki, tmp_path / "out")
    return Path(written[0])


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:  # pragma: no cover - depends on host browser install
            pytest.skip("chromium not installed; run `playwright install chromium`")
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Compile the bilingual site once per module and return its file:// URI."""
    index = _build_site(tmp_path_factory.mktemp("site"))
    return index.as_uri()


@pytest.fixture()
def page(browser):
    context = browser.new_context()
    pg = context.new_page()
    yield pg
    context.close()


# ---------------------------------------------------------------------------
# Routing: document routes vs in-page anchors
# ---------------------------------------------------------------------------


def test_clicking_nav_route_renders_document(page, site_url: str):
    page.goto(site_url)
    # Click the nav link for "Quick Start" (data-route=/getting-started)
    page.click('#sidebar a[data-route="/getting-started"]')
    page.wait_for_selector("#docViewer h1")
    assert page.eval_on_selector("#docViewer h1", "el => el.textContent") == "Quick Start"
    # Hash is the document route (leading slash).
    assert page.evaluate("window.location.hash") == "#/getting-started"


def test_in_page_anchor_does_not_navigate_away(page, site_url: str):
    page.goto(site_url)
    page.click('#sidebar a[data-route="/"]')
    page.wait_for_selector("#docViewer h2#architecture")
    # The rendered page has an anchor link. Click an in-page anchor.
    page.evaluate("window.location.hash = '#architecture'")
    page.wait_for_timeout(50)
    # Must NOT have been treated as a document route.
    assert page.evaluate("window.location.hash") == "#architecture"
    # The target heading exists in the DOM.
    assert page.evaluate("!!document.getElementById('architecture')")


def test_wiki_link_with_fragment_navigates_to_route_and_scrolls(page, site_url: str):
    page.goto(site_url)
    page.click('#sidebar a[data-route="/config"]')
    page.wait_for_selector("#docViewer h1")
    # The config doc links to getting-started#install (a wiki-link w/ fragment).
    link = page.locator('#docViewer a[data-anchor="install"]')
    assert link.count() == 1
    link.click()
    page.wait_for_timeout(100)
    # Document route changed, not just a same-page hash.
    assert page.evaluate("window.location.hash") == "#/getting-started"


# ---------------------------------------------------------------------------
# Search on / off
# ---------------------------------------------------------------------------


def test_search_on_filters_and_shortcut(page, site_url: str):
    page.goto(site_url)
    input_el = page.locator("#searchInput")
    assert input_el.count() == 1
    input_el.fill("install")
    page.wait_for_selector(".search-result")
    results = page.locator(".search-result")
    assert results.count() >= 1
    # '/' focuses the search box.
    page.keyboard.press("/")
    assert page.evaluate("document.activeElement.id") == "searchInput"


def test_search_disabled_site_renders_without_search(page, tmp_path: Path):
    index = _build_site(tmp_path, include_search=False)
    page.goto(index.as_uri())
    page.wait_for_selector("#docViewer h1")
    # No search input is rendered.
    assert page.locator("#searchInput").count() == 0
    # '/'' and Ctrl+K do not crash the page.
    page.keyboard.press("/")
    page.keyboard.press("Control+k")
    page.wait_for_timeout(50)
    assert page.evaluate("document.readyState") in ("interactive", "complete")


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------


def test_theme_toggle_persists_to_localstorage(page, site_url: str):
    page.goto(site_url)
    page.evaluate("localStorage.removeItem('site-theme')")
    page.reload()
    # Default theme is 'auto'; force to dark via the toggle.
    page.click("#themeToggle")
    assert page.eval_on_selector("html", "el => el.getAttribute('data-theme')") == "dark"
    stored = page.evaluate("localStorage.getItem('site-theme')")
    assert stored == "dark"
    # Reload persists the dark theme.
    page.reload()
    assert page.eval_on_selector("html", "el => el.getAttribute('data-theme')") == "dark"


def test_auto_theme_honors_prefers_color_scheme(page, browser, site_url: str):
    context = browser.new_context(color_scheme="dark")
    pg = context.new_page()
    pg.goto(site_url)
    pg.evaluate("localStorage.removeItem('site-theme')")
    pg.reload()
    # No explicit stored theme -> auto -> dark because prefers-color-scheme dark.
    assert pg.eval_on_selector("html", "el => el.getAttribute('data-theme')") == "dark"
    context.close()


# ---------------------------------------------------------------------------
# Language switching
# ---------------------------------------------------------------------------


def test_language_switch_updates_html_lang_and_title(page, site_url: str):
    page.goto(site_url)
    # Start in English.
    assert page.eval_on_selector("html", "el => el.getAttribute('lang')") == "en"
    page.select_option("#langSelect", "zh-CN")
    page.wait_for_timeout(100)
    assert page.eval_on_selector("html", "el => el.getAttribute('lang')") == "zh-CN"
    # The rendered doc title is the localized one.
    assert page.eval_on_selector("#docViewer h1", "el => el.textContent") == "示例项目"


def test_missing_translation_shows_fallback_notice(page, site_url: str):
    page.goto(site_url)
    # getting-started.zh-CN.md exists, so switch and go there.
    page.select_option("#langSelect", "zh-CN")
    page.wait_for_timeout(50)
    page.click('#sidebar a[data-route="/config"]')
    page.wait_for_timeout(100)
    # config has no zh-CN translation -> explicit fallback banner, not silent.
    assert page.locator(".fallback-banner").count() == 1
    # The fallback still shows the English (default) content.
    assert page.eval_on_selector("#docViewer h1", "el => el.textContent") == "Configuration"


# ---------------------------------------------------------------------------
# Mobile navigation
# ---------------------------------------------------------------------------


def test_mobile_drawer_opens_closes_with_escape(page, browser, site_url: str):
    context = browser.new_context(viewport={"width": 375, "height": 667})
    pg = context.new_page()
    pg.goto(site_url)
    pg.wait_for_selector("#hamburger")
    # On mobile the hamburger is visible; clicking opens the drawer.
    assert pg.locator("#hamburger").is_visible()
    pg.click("#hamburger")
    assert pg.eval_on_selector("#sidebar", "el => el.classList.contains('open')")
    assert pg.eval_on_selector("#hamburger", "el => el.getAttribute('aria-expanded')") == "true"
    # Escape closes the drawer.
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(100)
    assert not pg.eval_on_selector("#sidebar", "el => el.classList.contains('open')")
    context.close()


def test_desktop_hamburger_hidden(page, site_url: str):
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(site_url)
    assert not page.locator("#hamburger").is_visible()
    # Desktop sidebar is visible, not an off-canvas drawer.
    assert page.locator("#sidebar").is_visible()


# ---------------------------------------------------------------------------
# Table of contents
# ---------------------------------------------------------------------------


def test_toc_lists_h2_and_h3(page, site_url: str):
    page.goto(site_url)
    page.click('#sidebar a[data-route="/getting-started"]')
    page.wait_for_selector("#docViewer h1")
    toc_links = page.locator("#tocPanel a")
    labels = toc_links.all_text_contents()
    assert "Install" in labels
    assert "Verifying" in labels  # H3
    assert "Architecture" not in labels  # different doc


def test_toc_scrollspy_highlights_active(page, site_url: str):
    page.goto(site_url)
    # Wait until the home doc renders and the TOC is populated.
    page.wait_for_selector("#docViewer h2#architecture")
    page.wait_for_selector("#tocPanel a")
    page.evaluate("window.scrollTo(0, document.getElementById('architecture').offsetTop)")
    page.wait_for_timeout(300)
    active = page.eval_on_selector("#tocPanel a.active", "el => (el ? el.textContent : null)")
    assert active == "Architecture"


# ---------------------------------------------------------------------------
# Code copy
# ---------------------------------------------------------------------------


def test_code_copy_button_shows_copied(page, site_url: str):
    page.goto(site_url)
    page.click('#sidebar a[data-route="/getting-started"]')
    page.wait_for_selector("#docViewer pre .copy-btn")
    # Stub the clipboard API (file:// is not a secure context).
    page.evaluate(
        """() => {
          const calls = [];
          Object.defineProperty(navigator, 'clipboard', {
            value: { writeText: (t) => { calls.push(t); return Promise.resolve(); } },
            configurable: true
          });
          window.__calls = calls;
        }"""
    )
    page.click("#docViewer pre .copy-btn")
    page.wait_for_timeout(100)
    # Button relabels to Copied! and the stubbed clipboard received the code.
    assert page.locator("#docViewer pre .copy-btn").text_content() == "Copied!"
    captured = page.evaluate("window.__calls")
    assert any("npm install" in c for c in captured)


# ---------------------------------------------------------------------------
# Broken / missing links
# ---------------------------------------------------------------------------


def test_broken_internal_link_does_not_crash(page, site_url: str):
    page.goto(site_url)
    page.click('#sidebar a[data-route="/config"]')
    page.wait_for_selector("#docViewer h1")
    # The config doc links out; missing-document navigation stays intact.
    page.evaluate("window.location.hash = '#/no-such-page'")
    page.wait_for_timeout(100)
    # Page still functional: can navigate back to a real route.
    page.click('#sidebar a[data-route="/"]')
    page.wait_for_selector("#docViewer h1")
    assert page.eval_on_selector("#docViewer h1", "el => el.textContent") == "Sample Project"


def test_initial_load_with_hash_routes(page, site_url: str):
    page.goto(site_url + "#/getting-started")
    page.wait_for_selector("#docViewer h1")
    assert page.eval_on_selector("#docViewer h1", "el => el.textContent") == "Quick Start"
