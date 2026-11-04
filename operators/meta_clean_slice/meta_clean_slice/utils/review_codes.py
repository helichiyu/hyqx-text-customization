"""原因码：复核 / 跳过 / 失败条目除中文原因外，附带机器可读 `code`。

平台按 `code` 分类统计（复核单触发条件、跳过/失败汇总），中文文案仍以 `reason` /
`reviewReason` 为准。约定：`code` 为小写下划线英文，跨算子语义一致；取首个命中条件
（优先级由算子按业务顺序传入），无命中时用 `unclassified` 兜底。
"""

from __future__ import annotations


def pick(*pairs: tuple[bool, str], default: str = "unclassified") -> str:
    """按传入顺序返回第一个命中条件的原因码。"""

    for hit, code in pairs:
        if hit:
            return code
    return default
