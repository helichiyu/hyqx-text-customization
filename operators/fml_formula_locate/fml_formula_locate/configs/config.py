"""fml_formula_locate 配置（公式文本交付说明 §三/§八）。"""

#: 渲染 DPI
RENDER_DPI = 150

#: 页图送入定位模型的长边上限
IMAGE_MAX_LONG_EDGE = 1600

#: 上下文文本最大长度（交付说明 §4.3：前后各 1–2 段，总长 ≤2000 字）
MAX_CONTEXT_CHARS = 2000

#: 裁切 bbox 最小面积（0–1000 归一化坐标系），过滤噪声框
MIN_BBOX_AREA = 20
