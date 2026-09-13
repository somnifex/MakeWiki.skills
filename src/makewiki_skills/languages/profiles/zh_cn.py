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
        "使用规范、地道的工程师书面中文撰写技术文档，用词准确专业，主谓宾完整。"
        "使用主动语态，动词先行，直奔操作主题。"
        "不写聊天腔（语气词'呀、啦、呗'，口语短语'咱们、搞定'）、"
        "公文腔（'综上所述、至关重要、有序推进'）与翻译腔（欧化长句、生硬被动句）。"
        "每句话只讲一件事，长句拆成短句；长短句交替，句句长短相仿是被机器抛光的节奏。"
        "每句话提供新信息；指称同一事物就近沿用同一个叫法，不为避重复升格换词。"
        "写具体的人、事、动作、原因、结果；形容词与副词只用于必要之处，程度用数字与细节呈现。"
        "细节与数据有出处；给不出出处的'研究表明、数据显示'删掉铺垫，不编造来源，不凭空添时间与场景。"
        "按事实本来的程度陈述，不拔高不升华；结尾在内容完结处收束，不加感想与展望。"
        "标点以逗号、句号为主；不用'首先、其次、最后'类结构词；"
        "逻辑关系用'但是、因此'写明，不靠'显然、值得注意'类提示词。"
        "严禁使用'不是……而是……'、'不仅……而且……'、'一句话总结'、'简单来说'、'对流程进行了优化'等AI套话，"
        "以及'赋能、抓手、沉淀、打法、势能、生态位、顶层设计、全链路、拉齐、打通、对标、倒逼、颗粒度'等黑话大词。"
        "术语、命令、代码与引用原样保留；改写只动说法，不动事实。"
        "严禁在标题和列表项中滥用冒号与冗余前缀。"
        "英文专有名词与命令保持原生大小写，中英文之间保留空格。"
    ),
    file_suffix=".zh-CN",
)
