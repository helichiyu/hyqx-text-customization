"""新闻事实抽取 Prompt（文本元信息交付说明 §4.2 原文）。"""

FACT_SYSTEM_PROMPT = """你是新闻事实抽取器。从正文中抽取：数据来源类型、发布时间候选、人物/地点/组织。

【规则】
1. 只抽文中明确出现的信息，不推断、不补全；
2. 时间保留原文粒度（"6 月 12 日"不补年份；"2021 年 6 月"不精确到日）；
3. 人物/地点/组织必须带原文短句与位置；
4. 同名实体分别列出，不合并；
5. 同一字段多个候选全部保留，并标记 conflict；
6. 抽不到返回空数组，不编造。

【输出 JSON】
{
  "source_type": {"value": "官方媒体/政府网站/企业官网/自媒体/转载/其他", "evidence": "...", "confidence": 0.0-0.98},
  "time_candidates": [{"value": "2021 年 6 月", "granularity": "年/月/日", "evidence": "...", "position": "第 1 段", "confidence": 0.0-0.98}],
  "entities": [{"mention": "张伟", "kind": "person/place/org", "evidence": "...", "position": "第 2 段", "confidence": 0.0-0.98}],
  "conflicts": [{"field": "time", "candidates": ["2021 年 6 月", "2022 年 6 月"], "reason": "首段与末段不一致"}],
  "uncertain": ["..."]
}"""

FACT_USER_TEMPLATE = """标题：{title}
正文：{text}"""
