"""Mechanical localized-filename resolution shared across consumers.

The MakeWiki filename contract (``LanguageProfile.file_suffix`` +
``LanguageProfile.get_filename``): the default language's content carries NO
suffix (``guide.md``) and every other declared language carries its suffix
before the extension (``guide.ja.md``). This module is the single mechanical
parser for that contract — consumers pass their declared language set and
default language; no language-code enumeration or text-based detection lives
here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocalizedFilename:
    """Resolution of one relative markdown path against declared languages."""

    base_id: str  # document/page id without language suffix (posix relative)
    language: str  # resolved language code
    declared: bool  # True when the path matches the declared language set


def resolve_localized_filename(
    rel: str,
    languages: list[str] | set[str],
    default_language: str,
) -> LocalizedFilename:
    """Resolve ``rel`` (posix relative markdown path) to (base_id, language).

    Contract (``LanguageProfile.get_filename``): a path ending
    ``.<lang>.md`` for a declared non-default ``<lang>`` belongs to that
    language with the suffix stripped; every other ``.md`` path is the plain
    default-language form — its base id is the stem minus ``.md`` (whatever
    dots it contains; the contract splits only the extension). No language
    code is guessed for undeclared suffix tokens: ``guide.xx.md`` with
    ``xx`` undeclared is simply the default-language document ``guide.xx``,
    and never joins ``guide``'s cross-language group.
    """
    if not rel.endswith(".md"):
        return LocalizedFilename(rel, default_language, False)
    for lang in sorted(set(languages) - {default_language}):
        suffix = f".{lang}.md"
        if rel.endswith(suffix):
            return LocalizedFilename(rel[: -len(suffix)], lang, True)
    return LocalizedFilename(rel[: -len(".md")], default_language, True)
