"""meta_clean_slice 配置：正文校验与切片参数（文本元信息交付说明 §三环节①、§八）。"""

#: 切片固定参数（交付说明：单片最大 2000 汉字，重叠 200 字（10%），章节→段落）
SLICE_MAX_CHARS = 2000
SLICE_OVERLAP_CHARS = 200

#: 正文校验阈值
MIN_READABLE_CHARS = 20      # 去标签后可读字符下限（空白页判定）
MIN_PARAGRAPH_CHARS = 20     # 有效段落最小长度
NAV_LINK_RATIO = 0.6         # 链接文字占比超过该值判导航页

#: 章节标题触发切片边界的条件：当前片已积累字符数达到该值时，遇到一级标题另起一片
CHAPTER_BREAK_MIN_CHARS = 1000
