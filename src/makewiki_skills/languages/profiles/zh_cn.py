"""Simplified Chinese (zh-CN) language profile."""

from makewiki_skills.languages.profile import (
    FormalityLevel,
    FormattingRules,
    LanguageProfile,
    TerminologyMap,
)

PROFILE = LanguageProfile(
    code="zh-CN",
    display_name="Simplified Chinese",
    native_name="\u7b80\u4f53\u4e2d\u6587",
    terminology=TerminologyMap(
        installation="\u5b89\u88c5",
        configuration="\u914d\u7f6e",
        getting_started="\u5feb\u901f\u5f00\u59cb",
        prerequisites="\u524d\u7f6e\u6761\u4ef6",
        usage="\u4f7f\u7528\u8bf4\u660e",
        basic_usage="\u57fa\u672c\u7528\u6cd5",
        commands="\u547d\u4ee4\u53c2\u8003",
        faq="\u5e38\u89c1\u95ee\u9898",
        troubleshooting="\u6545\u969c\u6392\u9664",
        note="\u6ce8\u610f",
        warning="\u8b66\u544a",
        tip="\u63d0\u793a",
        example="\u793a\u4f8b",
        optional="\u53ef\u9009",
        required="\u5fc5\u586b",
        default_value="\u9ed8\u8ba4\u503c",
        description="\u8bf4\u660e",
        command="\u547d\u4ee4",
        question="\u95ee\u9898",
        answer="\u89e3\u7b54",
        symptom="\u73b0\u8c61",
        solution="\u89e3\u51b3\u65b9\u6848",
        cause="\u53ef\u80fd\u539f\u56e0",
        next_steps="\u4e0b\u4e00\u6b65",
        table_of_contents="\u76ee\u5f55",
        what_is="\u4ec0\u4e48\u662f {name}\uff1f",
        who_is_it_for="\u9002\u5408\u8c01\u4f7f\u7528\uff1f",
        project_overview="\u6982\u8ff0",
        verify_installation="\u9a8c\u8bc1\u5b89\u88c5",
        quick_start="\u5feb\u901f\u5f00\u59cb",
        common_tasks="\u5e38\u89c1\u4efb\u52a1",
        platform_notes="\u5e73\u53f0\u8bf4\u660e",
        environment_variables="\u73af\u5883\u53d8\u91cf",
        related_docs="\u76f8\u5173\u6587\u6863",
    ),
    formality=FormalityLevel.NEUTRAL,
    formatting=FormattingRules(
        note_callout="> **\u6ce8\u610f\uff1a**",
        warning_callout="> **\u8b66\u544a\uff1a**",
        tip_callout="> **\u63d0\u793a\uff1a**",
        date_format="YYYY\u5e74MM\u6708DD\u65e5",
        use_fullwidth_punctuation=True,
        space_between_cjk_and_latin=True,
    ),
    generation_hints=(
        "\u7528\u7b80\u6d01\u3001\u4e13\u4e1a\u7684\u7b80\u4f53\u4e2d\u6587\u64b0\u5199\u6280\u672f\u6587\u6863\u3002"
        "\u4f7f\u7528\u4e3b\u52a8\u8bed\u6001\uff0c\u4ee5\u201c\u4f60\u201d\u79f0\u547c\u7528\u6237\u3002"
        "\u4fdd\u6301\u7b80\u6d01\u540c\u65f6\u786e\u4fdd\u51c6\u786e\u6027\uff0c\u82f1\u6587\u4e13\u6709\u540d\u8bcd\u4fdd\u7559\u82f1\u6587\u3002"
    ),
    file_suffix=".zh-CN",
)
