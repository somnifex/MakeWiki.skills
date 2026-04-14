"""English language profile."""

from makewiki_skills.languages.profile import (
    FormalityLevel,
    FormattingRules,
    LanguageProfile,
    TerminologyMap,
)

PROFILE = LanguageProfile(
    code="en",
    display_name="English",
    native_name="English",
    terminology=TerminologyMap(),  # defaults are already English
    formality=FormalityLevel.NEUTRAL,
    formatting=FormattingRules(
        note_callout="> **Note:**",
        warning_callout="> **Warning:**",
        tip_callout="> **Tip:**",
    ),
    generation_hints=(
        "Write in clear, professional technical English. "
        "Use active voice. Address the reader as 'you'. "
        "Be concise but complete."
    ),
    file_suffix="",  # default language - no suffix
)
