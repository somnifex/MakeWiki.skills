"""Japanese language profile."""

from makewiki_skills.languages.profile import (
    FormalityLevel,
    FormattingRules,
    LanguageProfile,
    TerminologyMap,
)

PROFILE = LanguageProfile(
    code="ja",
    display_name="Japanese",
    native_name="\u65e5\u672c\u8a9e",
    terminology=TerminologyMap(
        installation="\u30a4\u30f3\u30b9\u30c8\u30fc\u30eb",
        configuration="\u8a2d\u5b9a",
        getting_started="\u306f\u3058\u3081\u306b",
        prerequisites="\u524d\u63d0\u6761\u4ef6",
        usage="\u4f7f\u3044\u65b9",
        basic_usage="\u57fa\u672c\u7684\u306a\u4f7f\u3044\u65b9",
        commands="\u30b3\u30de\u30f3\u30c9\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9",
        faq="\u3088\u304f\u3042\u308b\u8cea\u554f",
        troubleshooting="\u30c8\u30e9\u30d6\u30eb\u30b7\u30e5\u30fc\u30c6\u30a3\u30f3\u30b0",
        note="\u6ce8\u610f",
        warning="\u8b66\u544a",
        tip="\u30d2\u30f3\u30c8",
        example="\u4f8b",
        optional="\u4efb\u610f",
        required="\u5fc5\u9808",
        default_value="\u30c7\u30d5\u30a9\u30eb\u30c8",
        description="\u8aac\u660e",
        command="\u30b3\u30de\u30f3\u30c9",
        question="\u8cea\u554f",
        answer="\u56de\u7b54",
        symptom="\u75c7\u72b6",
        solution="\u89e3\u6c7a\u7b56",
        cause="\u539f\u56e0",
        next_steps="\u6b21\u306e\u30b9\u30c6\u30c3\u30d7",
        table_of_contents="\u76ee\u6b21",
        what_is="{name} \u3068\u306f\uff1f",
        who_is_it_for="\u5bfe\u8c61\u30e6\u30fc\u30b6\u30fc",
        project_overview="\u6982\u8981",
        verify_installation="\u30a4\u30f3\u30b9\u30c8\u30fc\u30eb\u306e\u78ba\u8a8d",
        quick_start="\u30af\u30a4\u30c3\u30af\u30b9\u30bf\u30fc\u30c8",
        common_tasks="\u4e00\u822c\u7684\u306a\u30bf\u30b9\u30af",
        platform_notes="\u30d7\u30e9\u30c3\u30c8\u30d5\u30a9\u30fc\u30e0\u5225\u306e\u6ce8\u610f\u4e8b\u9805",
        environment_variables="\u74b0\u5883\u5909\u6570",
        related_docs="\u95a2\u9023\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8",
    ),
    formality=FormalityLevel.FORMAL,
    formatting=FormattingRules(
        note_callout="> **\u6ce8\u610f\uff1a**",
        warning_callout="> **\u8b66\u544a\uff1a**",
        tip_callout="> **\u30d2\u30f3\u30c8\uff1a**",
        date_format="YYYY\u5e74MM\u6708DD\u65e5",
        use_fullwidth_punctuation=True,
        space_between_cjk_and_latin=False,
    ),
    generation_hints=(
        "\u4e01\u5be7\u3067\u6b63\u78ba\u306a\u65e5\u672c\u8a9e\u3067\u6280\u8853\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\u3092\u4f5c\u6210\u3057\u3066\u304f\u3060\u3055\u3044\u3002"
        "\u3067\u3059\u30fb\u307e\u3059\u8abf\u3092\u4f7f\u7528\u3057\u3001\u5c02\u9580\u7528\u8a9e\u306f\u30ab\u30bf\u30ab\u30ca\u307e\u305f\u306f\u82f1\u8a9e\u306e\u307e\u307e\u4f7f\u3063\u3066\u304f\u3060\u3055\u3044\u3002"
    ),
    file_suffix=".ja",
)
