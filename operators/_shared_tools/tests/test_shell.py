"""外壳三接口契约测试：脚手架 → 桩核心换成演示核心 → uploadFile/predict/removeFile 全流程。"""

import importlib
import io
import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

SHARED = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SHARED))

import gen_inference  # noqa: E402


@pytest.fixture()
def demo_app(tmp_path, monkeypatch):
    gen_inference.scaffold()
    tag = "meta_clean_slice"
    root = gen_inference.OPERATORS_ROOT / tag

    # 换成演示核心：把输入文件名写入 JSONL
    sys.path.insert(0, str(root))
    pkg = __import__(f"{tag}.operator", fromlist=["operator"])

    def demo_run(input_dir, output_dir, params, log):
        files = sorted(p.name for p in input_dir.iterdir() if p.is_file())
        (output_dir / "records.jsonl").write_text(
            "".join(json.dumps({"file": f}, ensure_ascii=False) + "\n" for f in files),
            encoding="utf-8",
        )
        return {
            "records_file": "records.jsonl",
            "summary": {"total": len(files)},
            "skipped": [],
            "failed": [],
            "sample_lineage": [{"sample_id": f, "action": "keep"} for f in files],
        }

    pkg.run = demo_run

    monkeypatch.setenv("INPUT_DIR", str(tmp_path / "input"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))

    spec = importlib.util.spec_from_file_location("demo_inference", root / "inference.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from fastapi.testclient import TestClient

    return TestClient(mod.app), tmp_path


def _make_zip(names=("a.html", "b.html", "c.exe")) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n in names:
            zf.writestr(f"sub/dir/{n}", f"content of {n}")
    return buf.getvalue()


def test_three_interfaces(demo_app):
    client, tmp_path = demo_app

    r = client_healthz = demo_app[0].get("/healthz")
    assert r.status_code == 200 and r.json()["data"]["operator"] == "meta_clean_slice"

    # 上传 zip：.exe 不在白名单被剔除并记录
    r = demo_app[0].post(
        "/uploadFile?uniqueId=t001",
        files={"file": ("pack.zip", _make_zip(), "application/zip")},
    )
    body = r.json()
    assert body["code"] == 0, body
    assert sorted(body["data"]["files"]) == ["a.html", "b.html"]
    assert body["data"]["skipped"] and body["data"]["skipped"][0]["name"] == "c.exe"

    # predict（阶段首，凭 uniqueId；isLastOperator 打 zip）
    r = demo_app[0].post("/predict", json={"uniqueId": "t001", "isLastOperator": True})
    body = r.json()
    assert body["code"] == 0, body
    out = Path(body["data"]["outputFile"])
    lin = Path(body["data"]["lineageFile"])
    assert out.suffix == ".zip" and out.exists()
    assert lin.exists()
    lines = lin.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["record_type"] == "task_lineage"
    assert len(lines) == 3  # 1 任务头 + 2 样本

    with zipfile.ZipFile(out) as zf:
        assert "records.jsonl" in zf.namelist()

    # predict（阶段内，凭 inputFile）
    r = demo_app[0].post("/predict", json={"inputFile": str(tmp_path / "input" / "t001")})
    assert r.json()["code"] == 0, r.json()

    # inputFile 越界拒绝
    r = demo_app[0].post("/predict", json={"inputFile": "C:/Windows"})
    assert r.json()["code"] == 1

    # removeFile 幂等
    r1 = demo_app[0].post("/removeFile?uniqueId=t001")
    r2 = demo_app[0].post("/removeFile?uniqueId=t001")
    assert r1.json()["data"]["deleted"] is True
    assert r2.json()["data"]["deleted"] is False and r2.json()["code"] == 0

    # uniqueId 非法
    r = demo_app[0].post("/removeFile?uniqueId=../evil")
    assert r.json()["code"] == 1


def test_healthz_only():
    """空算子（桩核心）也能起服务、healthz 通。"""
    gen_inference.scaffold()
