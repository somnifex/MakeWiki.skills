"""French language profile."""

from makewiki_skills.languages.profile import (
    FormalityLevel,
    FormattingRules,
    LanguageProfile,
    TerminologyMap,
)

PROFILE = LanguageProfile(
    code="fr",
    display_name="French",
    native_name="Fran\u00e7ais",
    terminology=TerminologyMap(
        installation="Installation",
        configuration="Configuration",
        getting_started="Prise en main",
        prerequisites="Pr\u00e9requis",
        usage="Utilisation",
        basic_usage="Utilisation de base",
        commands="R\u00e9f\u00e9rence des commandes",
        faq="Foire aux questions",
        troubleshooting="D\u00e9pannage",
        note="Note",
        warning="Avertissement",
        tip="Conseil",
        example="Exemple",
        optional="optionnel",
        required="requis",
        default_value="Valeur par d\u00e9faut",
        description="Description",
        command="Commande",
        question="Question",
        answer="R\u00e9ponse",
        symptom="Sympt\u00f4me",
        solution="Solution",
        cause="Cause probable",
        next_steps="\u00c9tapes suivantes",
        table_of_contents="Table des mati\u00e8res",
        what_is="Qu\u2019est-ce que {name}\u00a0?",
        who_is_it_for="\u00c0 qui s\u2019adresse ce projet\u00a0?",
        project_overview="Pr\u00e9sentation",
        verify_installation="V\u00e9rifier l\u2019installation",
        quick_start="D\u00e9marrage rapide",
        common_tasks="T\u00e2ches courantes",
        platform_notes="Notes par plateforme",
        environment_variables="Variables d\u2019environnement",
        related_docs="Documentation connexe",
    ),
    formality=FormalityLevel.NEUTRAL,
    formatting=FormattingRules(
        note_callout="> **Note\u00a0:**",
        warning_callout="> **Avertissement\u00a0:**",
        tip_callout="> **Conseil\u00a0:**",
        number_format="1\u00a0000",
    ),
    generation_hints=(
        "R\u00e9digez une documentation technique claire et professionnelle en fran\u00e7ais. "
        "Utilisez le vouvoiement. Les termes techniques anglais couramment utilis\u00e9s "
        "peuvent \u00eatre conserv\u00e9s tels quels."
    ),
    file_suffix=".fr",
)
