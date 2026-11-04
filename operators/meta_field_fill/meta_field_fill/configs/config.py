"""meta_field_fill 配置：阈值、字段清单与枚举。"""

#: 补全质量阈值（交付说明 §八：抽取/补全阈值默认 0.80，任务级可调）
FILL_CONFIDENCE_THRESHOLD = 0.8

#: 送入模型的正文最大字符（多片拼接后截断，防止超长上下文）
MAX_TEXT_CHARS = 6000

#: 16 字段清单（交付说明 §4.3 / §五，顺序固定）
STRUCTURED_FIELDS = ["数据来源类型", "可能的发布时间", "涉及人物、地点或组织", "时空变迁信息"]
BASIC_FIELDS = ["知识层次", "涉及的知识点列表", "主要一级行业", "行业场景", "行业类型", "涉及的角色列表"]
RELATED_FIELDS = ["文章风格", "内容类别", "价值观", "历史关联", "国家关联", "宗教关联"]
FIELD_GROUPS = {"structured": STRUCTURED_FIELDS, "basic": BASIC_FIELDS, "related": RELATED_FIELDS}

#: 枚举校验
KNOWLEDGE_LEVELS = {"大众常识", "基础教育", "学术研究", "技术应用"}
VALUES_ORIENTATIONS = {"褒", "贬", "中性"}

#: 列表型字段（value 应为数组）
LIST_FIELDS = {"涉及人物、地点或组织", "涉及的知识点列表", "涉及的角色列表"}
