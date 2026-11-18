"""共享 BERT tokenizer 包装（#26 MLM / #37 Token序列 同源口径）。

- HFBertTokenizer：transformers 可用时从本地词表目录装载（BERT-base-Chinese，
  词表在各算子 weight/ 目录自带，离线可用）；token 级精确
- CharTokenizer：无 transformers 环境的字符级降级（中文≈1字1token）——
  仅供 #26 在瘦环境可用（掩码逻辑可测），#37 的产物是词表 id，必须真词表

线程安全：tokenizer 只读共享（规范 11.2 单例语义）。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Optional

# 字符级降级模式的随机替换候选池（真实模式从词表采样）
_FALLBACK_RANDOM_POOL = "的一是了我不人在他有这上们来到时大地为子中你说生国年着就那和要她出也得里后自以会家可下而过天去能对小多然于心学么之都好看起发当没成只如事把还用第样道想作种开"
_SPECIALS = ("[CLS]", "[SEP]", "[MASK]", "[PAD]", "[UNK]")


def vocab_sha256(weight_dir) -> Optional[str]:
    vocab = Path(weight_dir) / "vocab.txt"
    if not vocab.exists():
        return None
    return hashlib.sha256(vocab.read_bytes()).hexdigest()


class CharTokenizer:
    """字符级降级：中文≈1字1token。不入词表 id 产物使用（#37 禁用）。"""

    name = "char-fallback"
    mask_token = "[MASK]"
    cls_token = "[CLS]"
    sep_token = "[SEP]"
    pad_token = "[PAD]"

    def tokenize(self, text: str) -> List[str]:
        return [ch for ch in text if not ch.isspace()]

    def convert_tokens_to_string(self, tokens: List[str]) -> str:
        return "".join(tokens)

    def random_token(self, rng) -> str:
        return _FALLBACK_RANDOM_POOL[rng.randrange(len(_FALLBACK_RANDOM_POOL))]

    def is_special(self, token: str) -> bool:
        return token in _SPECIALS


class HFBertTokenizer:
    """真词表（BERT-base-Chinese WordPiece）。name/方法集与 CharTokenizer 对齐。"""

    def __init__(self, weight_dir):
        from transformers import BertTokenizerFast

        self._tok = BertTokenizerFast.from_pretrained(str(weight_dir))
        self.name = f"bert-wordpiece:{Path(weight_dir).name}"

    @property
    def mask_token(self):
        return self._tok.mask_token

    @property
    def cls_token(self):
        return self._tok.cls_token

    @property
    def sep_token(self):
        return self._tok.sep_token

    @property
    def pad_token(self):
        return self._tok.pad_token

    def tokenize(self, text: str) -> List[str]:
        return self._tok.tokenize(text)

    def convert_tokens_to_string(self, tokens: List[str]) -> str:
        return self._tok.convert_tokens_to_string(tokens)

    def random_token(self, rng) -> str:
        vocab_size = self._tok.vocab_size
        for _ in range(10):  # 避开特殊 token 区间
            idx = rng.randrange(1000, vocab_size)
            token = self._tok.convert_ids_to_tokens(idx)
            if token not in _SPECIALS and not token.startswith("["):
                return token
        return "的"

    def is_special(self, token: str) -> bool:
        return token in _SPECIALS


def load_tokenizer(weight_dir, allow_fallback: bool = True):
    """优先真词表；不可用时降级（allow_fallback=False 用于 #37：缺词表即失败）。"""
    weight = Path(weight_dir)
    if (weight / "vocab.txt").exists():
        try:
            return HFBertTokenizer(weight)
        except ImportError:
            pass
    if allow_fallback:
        return CharTokenizer()
    raise RuntimeError(
        f"MODEL_LOAD_FAIL: 需要真实 BERT 词表（{weight}）且环境须安装 transformers"
    )
