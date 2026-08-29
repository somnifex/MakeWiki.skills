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
    native_name="简体中文",
    terminology=TerminologyMap(
        installation="安装指南",
        configuration="配置参考",
        getting_started="快速起步",
        prerequisites="环境要求",
        usage="使用手册",
        basic_usage="基本操作",
        commands="命令列表",
        faq="常见问题",
        troubleshooting="故障排查",
        note="说明",
        warning="注意",
        tip="提示",
        example="示例",
        optional="可选",
        required="必填",
        default_value="默认值",
        description="说明",
        command="命令",
        question="问题",
        answer="解答",
        symptom="异常现象",
        solution="解决步骤",
        cause="产生原因",
        next_steps="后续指引",
        table_of_contents="目录导航",
        what_is="{name} 功能概述",
        who_is_it_for="适用场景",
        project_overview="项目概览",
        verify_installation="验证安装",
        quick_start="快速起步",
        common_tasks="高频操作",
        platform_notes="平台兼容说明",
        environment_variables="环境变量参考",
        related_docs="文档索引",
    ),
    formality=FormalityLevel.NEUTRAL,
    formatting=FormattingRules(
        note_callout="> **说明**",
        warning_callout="> **注意**",
        tip_callout="> **提示**",
        date_format="YYYY年MM月DD日",
        use_fullwidth_punctuation=True,
        space_between_cjk_and_latin=True,
    ),
    generation_hints=(
        "使用地道、简洁的工程师中文撰写技术文档。"
        "使用主动语态，动词先行，直奔操作主题。"
        "严禁使用'不是……而是……'、'不仅……而且……'、'收敛'、'这是……'等AI套话与大词。"
        "严禁在标题和列表项中滥用冒号与冗余前缀。"
        "英文专有名词与命令保持原生大小写，中英文之间保留空格。"
    ),
    file_suffix=".zh-CN",
)
