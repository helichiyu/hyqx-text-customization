"""四条产线 HTTP 链路调用示例（对接前后端联调用）。

前置：release 目录内已解压全部算子 zip，并 `docker compose up -d --build` 起服务。

用法（在本文件所在目录执行）：
    python chain_example.py meta            # 文本元信息线：HTML → 数据集行（阶段 zip）
    python chain_example.py lay             # 复杂版面线：PDF → 一页一行
    python chain_example.py fml             # 公式文本线：PDF → 一个公式一行
    python chain_example.py img [几何]      # 图文融合线：图片 → 一张一行（第二参数为任务大类）

演示完整时序：uploadFile（仅阶段首）→ 逐算子 predict（inputFile 接续）→ 阶段 zip → removeFile。
"""

from __future__ import annotations

import io
import json
import sys
import time
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent

# 产线编排顺序与宿主机端口（与 docker-compose.yml 一致）
LINES: dict[str, list[tuple[str, int]]] = {
    "meta": [("meta_clean_slice", 6301), ("meta_genre_judge", 6302),
             ("meta_fact_extract", 6303), ("meta_field_fill", 6304)],
    "lay": [("lay_page_render", 6305), ("lay_page_detect", 6306)],
    "fml": [("fml_formula_locate", 6307), ("fml_formula_recognize", 6308)],
    "img": [("img_region_locate", 6309), ("img_type_classify", 6310),
            ("img_struct_describe", 6311)],
}


def base(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def predict(tag: str, port: int, body: dict) -> dict:
    """调一次 /predict；成功返回 data，业务失败直接抛出（code=1 + 中文原因）。"""
    r = requests.post(f"{base(port)}/predict", json=body, timeout=1800)
    payload = r.json()
    if payload.get("code") != 0:
        raise SystemExit(f"[FAIL] {tag}: {payload.get('msg')}")
    return payload["data"]


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in LINES:
        raise SystemExit(__doc__)
    line = sys.argv[1]
    category = sys.argv[2] if line == "img" and len(sys.argv) > 2 else "几何"
    chain = LINES[line]
    unique_id = f"demo_{line}_{int(time.time())}"

    # 0) 就绪探针
    for tag, port in chain:
        requests.get(f"{base(port)}/healthz", timeout=10).raise_for_status()
    print(f"[0] {len(chain)} 个算子就绪：{line} 线 {' → '.join(t for t, _ in chain)}")

    # 1) 阶段首：打包包内样本上传（真实场景由平台换成业务素材）
    first_tag = chain[0][0]
    sample_dir = ROOT / first_tag / first_tag / "dataset" / "sample"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(p for p in sample_dir.rglob("*") if p.is_file()):
            zf.write(f, f.name)
    r = requests.post(f"{base(chain[0][1])}/uploadFile",
                      params={"uniqueId": unique_id},
                      files={"file": (f"{line}_samples.zip", buf.getvalue(), "application/zip")},
                      timeout=300)
    assert r.json()["code"] == 0, r.text
    print(f"[1] uploadFile OK（uniqueId={unique_id}，{len(buf.getvalue()) // 1024} KB）")

    # 2) 链路：首环凭 uniqueId，其后凭 inputFile；末环 isLastOperator=true 收口阶段 zip
    body: dict = {"uniqueId": unique_id}
    data: dict = {}
    for i, (tag, port) in enumerate(chain, start=2):
        if i == len(chain) + 1:
            body["isLastOperator"] = True
        if tag == "img_type_classify":
            body["category"] = category  # 任务大类：几何/统计/表格/示意（任务创建时由前端传入）
        t0 = time.time()
        data = predict(tag, port, body)
        print(f"[{i}] {tag} OK（{time.time() - t0:.0f}s）summary={json.dumps(data['summary'], ensure_ascii=False)}")
        for s in data.get("skipped", []):
            print(f"    skip  {s['name']}: {s['reason']}")
        for f in data.get("failed", []):
            print(f"    fail  {f['name']}: {f['reason']}")
        body = {"inputFile": data["outputFile"]}  # 下一环的 inputFile = 上一环的 outputFile

    # 3) 阶段产物（末环收口的 zip：交复核/归集）
    print(f"[+] 阶段产物：{data['outputFile']}")
    print(f"[+] 血缘文件：{data['lineageFile']}")

    # 4) 幂等清理（真实场景由素材管理在任务结束后调用）
    requests.post(f"{base(chain[0][1])}/removeFile", params={"uniqueId": unique_id}, timeout=60)
    print("[4] removeFile OK（幂等，可重复调用）")


if __name__ == "__main__":
    main()
