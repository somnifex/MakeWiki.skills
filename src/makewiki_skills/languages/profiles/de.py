"""German language profile."""

from makewiki_skills.languages.profile import (
    FormalityLevel,
    FormattingRules,
    LanguageProfile,
    TerminologyMap,
)

PROFILE = LanguageProfile(
    code="de",
    display_name="German",
    native_name="Deutsch",
    terminology=TerminologyMap(
        installation="Installation",
        configuration="Konfiguration",
        getting_started="Erste Schritte",
        prerequisites="Voraussetzungen",
        usage="Verwendung",
        basic_usage="Grundlegende Verwendung",
        commands="Befehlsreferenz",
        faq="H\u00e4ufig gestellte Fragen",
        troubleshooting="Fehlerbehebung",
        note="Hinweis",
        warning="Warnung",
        tip="Tipp",
        example="Beispiel",
        optional="optional",
        required="erforderlich",
        default_value="Standardwert",
        description="Beschreibung",
        command="Befehl",
        question="Frage",
        answer="Antwort",
        symptom="Symptom",
        solution="L\u00f6sung",
        cause="M\u00f6gliche Ursache",
        next_steps="N\u00e4chste Schritte",
        table_of_contents="Inhaltsverzeichnis",
        what_is="Was ist {name}?",
        who_is_it_for="F\u00fcr wen ist es gedacht?",
        project_overview="\u00dcberblick",
        verify_installation="Installation \u00fcberpr\u00fcfen",
        quick_start="Schnellstart",
        common_tasks="H\u00e4ufige Aufgaben",
        platform_notes="Plattformhinweise",
        environment_variables="Umgebungsvariablen",
        related_docs="Verwandte Dokumentation",
    ),
    formality=FormalityLevel.FORMAL,
    formatting=FormattingRules(
        note_callout="> **Hinweis:**",
        warning_callout="> **Warnung:**",
        tip_callout="> **Tipp:**",
        number_format="1.000",
    ),
    generation_hints=(
        "Schreiben Sie klare, professionelle technische Dokumentation auf Deutsch. "
        "Verwenden Sie die Sie-Form. Fachbegriffe k\u00f6nnen auf Englisch bleiben, "
        "wenn sie im Deutschen \u00fcblich sind."
    ),
    file_suffix=".de",
)
