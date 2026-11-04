"""fml_formula_recognize 配置（公式文本交付说明 §三/§八）。"""

#: 识别/语义置信度阈值（两分数共用，任务级可配，默认 0.8）
CONFIDENCE_THRESHOLD = 0.8

#: 裁切图送入模型的长边上限（交付说明 §4.7：800–1200px）
IMAGE_MAX_LONG_EDGE = 1200
