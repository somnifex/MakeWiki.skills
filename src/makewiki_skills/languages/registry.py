"""Language registry - discover and load language profiles."""

from __future__ import annotations

from makewiki_skills.languages.profile import LanguageProfile


class LanguageNotFoundError(Exception):
    pass


class LanguageRegistry:
    """Central registry for language profiles."""

    _profiles: dict[str, LanguageProfile] = {}

    @classmethod
    def register(cls, profile: LanguageProfile) -> None:
        cls._profiles[profile.code] = profile

    @classmethod
    def get(cls, code: str) -> LanguageProfile:
        if code not in cls._profiles:
            raise LanguageNotFoundError(
                f"Language '{code}' is not registered. Available: {cls.list_codes()}"
            )
        return cls._profiles[code]

    @classmethod
    def list_codes(cls) -> list[str]:
        return sorted(cls._profiles.keys())

    @classmethod
    def has(cls, code: str) -> bool:
        return code in cls._profiles

    @classmethod
    def load_builtins(cls) -> None:
        from makewiki_skills.languages.profiles import de, en, fr, ja, zh_cn

        for mod in (en, fr, de, ja, zh_cn):
            cls.register(mod.PROFILE)

    @classmethod
    def reset(cls) -> None:
        cls._profiles.clear()
