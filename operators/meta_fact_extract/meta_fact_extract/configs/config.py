"""meta_fact_extract 配置：阈值。"""

#: 抽取质量阈值（交付说明 §八：抽取/补全阈值默认 0.80，任务级可调）
EXTRACTION_CONFIDENCE_THRESHOLD = 0.8

#: 来源类型枚举（交付说明 §4.2）
SOURCE_TYPES = ["官方媒体", "政府网站", "企业官网", "自媒体", "转载", "其他"]
