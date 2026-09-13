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
        "Be concise but complete. "
        "One idea per sentence; split long sentences and vary sentence length, "
        "since uniformly polished rhythm reads as machine-written. "
        "Keep one consistent name for the same thing instead of upgrading words "
        "to avoid repetition; every sentence adds new information. "
        "No AI-tic frames ('In summary', 'Simply put', 'It is worth noting', "
        "'It is not X, it is Y'). "
        "State facts at their true strength: no inflation, no uplifting closing. "
        "Never invoke sources you do not have ('studies show'); keep only the "
        "judgment that stands without them. "
        "Follow the skill's shared style guide (references/anti_ai_cliche.md)."
    ),
    file_suffix="",  # default language - no suffix
)
