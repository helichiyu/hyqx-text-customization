"""标准化文本记录 I/O 与编码检测。

编码检测逻辑迁移自 pretrain_text_service_demo/common/text_records.py（A 级复用）：
- BOM → 严格 UTF-8 → charset-normalizer / chardet 双库 → GB18030 兜底
- GB18030 纠偏启发式：短中文文本常被检测库误判为 cp949/big5
- jsonl 仅按真实换行符切行：splitlines 会把 JSON 字符串内的 U+0085/U+2028
  等 Unicode 行分隔符也当换行，撕裂合法 JSON（真实爬取语料实测踩中）

适配本组契约（规范第 3、4 章）：入口为上传字节流 parse_text_records()，
解析永不抛异常——失败信息写入记录 metadata（parseError/decodeFailed），
由各算子按业务语义决定打标还是放行（如 #2 异常过滤 / #10 编码归一化）。
"""

from __future__ import annotations

import codecs
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, List, Tuple

from common.operator_base import TextRecord


def _script_stats(text: str) -> Tuple[float, float, float, float]:
    """返回非 ASCII 字符中 汉字/假名/谚文/无效字符 的占比。"""
    chars = [ch for ch in text if ord(ch) > 127]
    total = len(chars) or 1
    cjk = kana = hangul = bad = 0
    for ch in chars:
        code = ord(ch)
        if (
            0x3400 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
            or 0x20000 <= code <= 0x2FA1F
            or 0x3000 <= code <= 0x303F  # 中文标点
            or 0xFF01 <= code <= 0xFF60  # 全角标点/字符
        ):
            cjk += 1
        elif 0x3040 <= code <= 0x30FF or 0x31F0 <= code <= 0x31FF or 0xFF66 <= code <= 0xFF9D:
            kana += 1
        elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF or 0x3130 <= code <= 0x318F:
            hangul += 1
        if (
            ch == "�"
            or 0xE000 <= code <= 0xF8FF
            or code >= 0xF0000
            or unicodedata.category(ch) in {"Cc", "Cn", "Co", "Cs"}
        ):
            bad += 1
    return cjk / total, kana / total, hangul / total, bad / total


def _prefer_gb18030(raw: bytes, encoding: str, detected_text: str) -> str:
    """中文语料修正：短文本检测库易误判为 cp949/big5，用 GB18030 结果对比。

    仅当 GB18030 解码后几乎全是汉字/无无效字符，且检测库结果既不是
    GB/UTF 编码、也不像日文/韩文时，才改判 GB18030，避免误伤日韩语料。
    """
    if encoding.lower().replace("_", "-").startswith(("gb", "utf", "big5", "cp950")):
        return encoding
    try:
        gb_text = raw.decode("gb18030")
    except UnicodeDecodeError:
        return encoding
    gb_cjk, _gb_kana, _gb_hangul, gb_bad = _script_stats(gb_text)
    detected_cjk, detected_kana, detected_hangul, _detected_bad = _script_stats(detected_text)
    if (
        gb_cjk >= 0.8
        and gb_bad == 0
        and detected_kana == 0
        and detected_hangul < 0.6
        and detected_cjk < 0.8
    ):
        return "gb18030"
    return encoding


def detect_text_encoding(raw: bytes, codec: str = "charset-normalizer") -> str:
    """检测文本编码（规范 #10：默认 charset-normalizer，GB18030 兜底）。

    先判 BOM 与严格 UTF-8，再交给检测库；检测结果必须能严格解码才算有效。
    无法识别时抛出 UnicodeDecodeError（#10 等算子按业务拦截打标）。
    """
    if not raw:
        return "utf-8"
    if raw.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    detected = None
    if codec.strip().lower() == "chardet":
        try:
            import chardet

            detected = chardet.detect(raw).get("encoding") or None
        except ImportError:
            detected = None
    if not detected:
        try:
            from charset_normalizer import from_bytes

            best = from_bytes(raw).best()
            if best is not None and best.encoding:
                detected = str(best.encoding)
        except ImportError:
            detected = None

    if detected:
        try:
            detected_text = raw.decode(detected)
        except (UnicodeDecodeError, LookupError):
            detected_text = ""
        if detected_text:
            return _prefer_gb18030(raw, detected, detected_text)

    # GB18030 覆盖 GBK/GB2312
    raw.decode("gb18030")
    return "gb18030"


def decode_text(raw: bytes, codec: str = "charset-normalizer") -> Tuple[str, str]:
    """按检测到的编码严格解码，返回 (文本, 编码)。"""
    encoding = detect_text_encoding(raw, codec)
    return raw.decode(encoding), encoding


def _record_from_value(value: Any, index: int) -> TextRecord:
    if isinstance(value, dict):
        record_id = str(value.get("id") or value.get("record_id") or f"record_{index:04d}")
        text = value.get("text")
        if text is None:
            text = value.get("content")
        if text is None:
            text = json.dumps(value, ensure_ascii=False)
        metadata = {k: v for k, v in value.items() if k not in {"id", "record_id", "text", "content"}}
        return TextRecord(record_id, str(text), metadata)
    return TextRecord(f"record_{index:04d}", str(value))


def _records_from_text(text: str, suffix: str, fallback_id: str) -> List[TextRecord]:
    records: List[TextRecord] = []
    if suffix == ".jsonl":
        for index, line in enumerate(text.split("\n"), 1):
            line = line.rstrip("\r")
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                # 单行 JSON 非法不中断整批，写入 parseError 由算子决定去向
                records.append(
                    TextRecord(
                        f"record_{index:04d}",
                        line,
                        {"parseError": f"JSONL 第 {index} 行解析失败: {exc}"},
                    )
                )
                continue
            if isinstance(value, list):
                # .jsonl 契约为每行一个对象；整行数组属格式错误（应存 .json），
                # 静默字符串化会造出一条假记录，标记 parseError
                records.append(
                    TextRecord(
                        f"record_{index:04d}",
                        line,
                        {"parseError": f"JSONL 第 {index} 行为 JSON 数组（契约要求每行一个对象，数组请使用 .json 文件）"},
                    )
                )
                continue
            records.append(_record_from_value(value, index))
        return records
    if suffix == ".json":
        value = json.loads(text)
        if isinstance(value, list):
            return [_record_from_value(item, i) for i, item in enumerate(value, 1)]
        return [_record_from_value(value, 1)]
    # txt/html/xml/doc 等原始文件：整体作为一条记录
    return [TextRecord(fallback_id or "record_0001", text)]


def parse_text_records(data: bytes, filename: str = "", codec: str = "charset-normalizer") -> List[TextRecord]:
    """解析上传文件字节流为记录列表（HTTP 壳入口）。解析失败不抛异常。"""
    if not data or not data.strip():
        return [TextRecord(Path(filename).stem or "record_0001", "", {"parseError": "空文件"})]
    try:
        text, _encoding = decode_text(data, codec)
    except (UnicodeDecodeError, LookupError) as exc:
        return [
            TextRecord(
                Path(filename).stem or "record_0001",
                "",
                {"decodeFailed": True, "parseError": f"编码无法识别或转换: {exc}"},
            )
        ]
    suffix = Path(filename).suffix.lower()
    try:
        return _records_from_text(text, suffix, Path(filename).stem)
    except json.JSONDecodeError as exc:
        return [
            TextRecord(
                Path(filename).stem or "record_0001",
                text,
                {"parseError": f"JSON 解析失败: {exc}"},
            )
        ]


def read_text_records(path: Path, codec: str = "charset-normalizer") -> List[TextRecord]:
    """从文件读取记录（本地测试/工具用，服务路径不走这里）。"""
    return parse_text_records(path.read_bytes(), path.name, codec)


def write_text_records(path: Path, records) -> None:
    """写出 jsonl（本地测试/工具用）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            payload = {"id": record.record_id, "text": record.text, **record.metadata}
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def visible_text(text: str) -> str:
    """空白归一化，用于对比与确定性校验。"""
    return re.sub(r"\s+", " ", text).strip()
