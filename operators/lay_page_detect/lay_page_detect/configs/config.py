"""lay_page_detect 配置：阈值与枚举（复杂版面交付说明 §三/§八）。"""

#: 低置信阈值（框选/判定共用，任务级可配，默认 0.8）
CONFIDENCE_THRESHOLD = 0.8

#: 重叠 IoU 阈值（固定 0.3）
IOU_THRESHOLD = 0.3

#: 元素类型枚举（交付说明 §4.1）
ELEMENT_TYPES = ["figure", "table", "formula", "heading", "body",
                 "header", "footer", "watermark", "special", "other"]

#: 页图送入模型的长边上限（交付说明 §4.5：1600–2000px；取下限 1600 降低时延，实测 17s/页）
IMAGE_MAX_LONG_EDGE = 1600
