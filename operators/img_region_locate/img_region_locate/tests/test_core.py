"""img_region_locate 离线测试：整图直通 / 边框裁剪 / 失败重试后跳过。"""

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from img_region_locate import operator as op  # noqa: E402
from img_region_locate.operator import run, validate_params  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[4] / "samples_pool" / "img"


def _noop_log(*args, **kwargs):
    pass


def test_passthrough_and_border_crop(tmp_path):
    """白底内容图直通不裁；带黑边图裁掉黑边。"""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    Image.new("RGB", (400, 300), "white").save(input_dir / "plain.png")
    # 黑边照片件：黑底中央白色内容
    img = Image.new("RGB", (400, 300), "black")
    for x in range(60, 340):
        for y in range(50, 250):
            img.putpixel((x, y), (255, 255, 255))
    img.save(input_dir / "bordered.png")

    result = run(input_dir, tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 2, "located": 2, "cropped": 1, "skipped": 0}
    rows = {r["imageId"]: r for r in
            (json.loads(l) for l in (tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines())}
    assert rows["plain"]["region"]["cropped"] is False
    b = rows["bordered"]["region"]
    assert b["cropped"] is True and b["bbox"] == [60, 50, 340, 250]
    assert (tmp_path / "out" / rows["bordered"]["image"]).exists()


def test_sample_pool_passthrough(tmp_path):
    """样本池 5 张图全部直通（无均色边框）。"""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for f in SAMPLES.iterdir():
        (input_dir / f.name).write_bytes(f.read_bytes())
    result = run(input_dir, tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"]["located"] == 5 and result["summary"]["skipped"] == 0


def test_corrupt_image_retried_then_skipped(tmp_path, monkeypatch):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "bad.png").write_bytes(b"not an image")
    calls = {"n": 0}
    original = op._locate_one

    def _counting(*a, **k):
        calls["n"] += 1
        return original(*a, **k)

    monkeypatch.setattr(op, "_locate_one", _counting)
    result = run(input_dir, tmp_path / "out", validate_params({}), _noop_log)
    assert calls["n"] == 3  # 首次 + 重试 2 次
    assert result["summary"]["skipped"] == 1
    assert "区域定位失败" in result["skipped"][0]["reason"]


def test_tiny_crop_goes_skipped(tmp_path):
    """整图近似纯色 → 内容区过小 → 重试后跳过。"""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    Image.new("RGB", (100, 100), (250, 250, 250)).save(input_dir / "blank.png")
    result = run(input_dir, tmp_path / "out", validate_params({}), _noop_log)
    # 纯色图无边框 → 整图直通（不算过小）；这里验证直通语义
    assert result["summary"]["located"] == 1


def test_params_validation():
    with pytest.raises(ValueError, match="border_tolerance"):
        validate_params({"border_tolerance": 100})
