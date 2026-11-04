# 图片区域定位与裁切（图文融合）测试指令

按顺序执行即可完成一次完整验收。命令按 Git Bash 写；换 Linux 容器把 `PY` 换成 `python3`。
Python 3.12、Pillow（四角背景色基准 + 差分掩码 + 裁切）；HTTP 层 FastAPI + uvicorn；不联网。

---

## 0. 前置准备

### 0.1 Python 与依赖

```bash
PY=/d/anaconda3/envs/use/python.exe
$PY -V    # 3.12
$PY -m pip install -r requirements.txt
```

### 0.2 工作目录与运行时目录

工作目录始终是交付包根（本文件所在目录）；临时文件放 `$WORK`（纯 ASCII 路径）。

```bash
cd <交付包根>
TAG=img_region_locate
WORK=$($PY -c "import os,tempfile;p=os.path.join(tempfile.gettempdir(),'opimg_region_locate');print(p.replace(os.sep,'/'))")
mkdir -p "$WORK/input" "$WORK/outputs"
```

---

## 1. 起服务

```bash
INPUT_DIR="$WORK/input" \
OUTPUT_DIR="$WORK/outputs" \
PYTHONIOENCODING=utf-8 \
$PY -m uvicorn inference:app --host 0.0.0.0 --port 6288
```

---

## 2. `GET /healthz`

```bash
curl -s http://127.0.0.1:6288/healthz
```

期望：`code=0`、算子名与 map.json 一致。

---

## 3. `POST /uploadFile`（阶段首算子上传形态）

```bash
# 打包样本（包内素材自足）
$PY - <<PY
import zipfile, pathlib
src = pathlib.Path("$TAG/dataset/sample")
with zipfile.ZipFile("$WORK/in.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(src.rglob("*")):
        if p.is_file():
            z.write(p, p.name)
print("ok")
PY

curl -s -X POST "http://127.0.0.1:6288/uploadFile?uniqueId=smoke001" -F "file=@$WORK/in.zip"
```

期望：`code=0`；后缀不在白名单的条目被跳过并记录原因；同一 uniqueId 重传先清空旧素材。

## 4. `POST /predict`

```bash
cat > "$WORK/predict.json" <<'JSON'
{"uniqueId":"smoke001","isLastOperator":false}
JSON
curl -s -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" --data-binary @"$WORK/predict.json"
```

uniqueId 已与第 3 步上传一致。
期望：`code=0`；`data.summary` 计数与包内样本一致（分支覆盖见说明书「训练后的模型性能指标」）；
`data.skipped` / `data.failed` 给出中文原因与机器码 `code`。

阶段首算子：不带 inputFile；判型 img_type_classify 接续。

---

## 5. 产物校验

```bash
cd "$WORK/outputs" && ls
# 找到最新 img_region_locate_run_* 目录；isLastOperator=true 时为 <run_id>_stage_output.zip
head -n 2 "$WORK/outputs"/img_region_locate_run_*/records.jsonl    # 主成果前两行
head -n 3 "$WORK/outputs"/img_region_locate_run_*/lineage_*.jsonl  # 血缘首行 + 样本行
```

期望要点：

- 主成果一张一行，字段与交付说明数据集明细一致；
- 血缘首行 `record_type: task_lineage`，其后逐样本 `sample_lineage`。


---

## 6. `POST /removeFile`（幂等）

```bash
curl -s -X POST "http://127.0.0.1:6288/removeFile?uniqueId=smoke001"
curl -s -X POST "http://127.0.0.1:6288/removeFile?uniqueId=smoke001"   # 再删一次
```

期望：两次都 `code=0`（第二次 `deleted=false`），幂等。

---

## 7. 负例（各回 code=1 与中文原因，HTTP 仍 200）

```bash
# a) predict 既无 uniqueId 也无 inputFile
curl -s -X POST http://127.0.0.1:6288/predict -H "Content-Type: application/json" -d '{}'

# b) inputFile 越界（路径闸门只放行 INPUT_DIR/OUTPUT_DIR 之内）
curl -s -X POST http://127.0.0.1:6288/predict -H "Content-Type: application/json" \
  -d '{"inputFile":"C:/Windows/notepad.exe"}'

# c) inputFile 在界内但不存在
curl -s -X POST http://127.0.0.1:6288/predict -H "Content-Type: application/json" \
  -d '{"inputFile":"$WORK/outputs/no_such_dir"}'

# d) 算子参数非法（border_tolerance 须在 0–255 之间）
curl -s -X POST http://127.0.0.1:6288/predict -H "Content-Type: application/json" \
  -d '{"uniqueId":"smoke001","border_tolerance":999}'
```

---

## 8. 复跑单元测试

```bash
cd <交付包根>
$PY -m pytest img_region_locate/tests -q
```

期望：全部通过（5 / 5 通过；离线用例 mock 模型调用，不联网）。
