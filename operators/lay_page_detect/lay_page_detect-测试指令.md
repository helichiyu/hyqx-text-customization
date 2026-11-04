# 逐页版面检测（复杂版面）测试指令

按顺序执行即可完成一次完整验收。命令按 Git Bash 写；换 Linux 容器把 `PY` 换成 `python3`。
Python 3.12、requests（VL 模型多模态调用）+ Pillow（框选图层）+ ThreadPoolExecutor；HTTP 层 FastAPI + uvicorn；模型调用走硅基流动 API（需可出网）。

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
TAG=lay_page_detect
WORK=$($PY -c "import os,tempfile;p=os.path.join(tempfile.gettempdir(),'oplay_page_detect');print(p.replace(os.sep,'/'))")
mkdir -p "$WORK/input" "$WORK/outputs"
```

---

## 1. 起服务

```bash
INPUT_DIR="$WORK/input" \
OUTPUT_DIR="$WORK/outputs" \
PYTHONIOENCODING=utf-8 \
$PY -m uvicorn inference:app --host 0.0.0.0 --port 6288 \
  SILICONFLOW_API_KEY=<密钥>
```

---

## 2. `GET /healthz`

```bash
curl -s http://127.0.0.1:6288/healthz
```

期望：`code=0`、算子名与 map.json 一致。

---

## 3. `POST /uploadFile`（本算子为链路中段）

正常形态经 `inputFile` 接续上游产物，不走 uploadFile。包内 `dataset/sample/` 预置了
上游真实产物，第 4 步直接以它作为 inputFile 喂入：

```bash
WORK_IN=$(cd "$TAG/dataset/sample" && pwd -W 2>/dev/null || cd "$TAG/dataset/sample" && pwd)
echo "upstream sample = $WORK_IN"
```

## 4. `POST /predict`

```bash
cat > "$WORK/predict.json" <<'JSON'
{"inputFile":"<上游 outputFile>","isLastOperator":true}
JSON
curl -s -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" --data-binary @"$WORK/predict.json"
```

把 `<上游 outputFile>` 替换为第 3 步的 $WORK_IN 路径。
期望：`code=0`；`data.summary` 计数与包内样本一致（分支覆盖见说明书「训练后的模型性能指标」）；
`data.skipped` / `data.failed` 给出中文原因与机器码 `code`。

产线末位：isLastOperator=true 收口阶段 zip。

---

## 5. 产物校验

```bash
cd "$WORK/outputs" && ls
# 找到最新 lay_page_detect_run_* 目录；isLastOperator=true 时为 <run_id>_stage_output.zip
head -n 2 "$WORK/outputs"/lay_page_detect_run_*/records.jsonl    # 主成果前两行
head -n 3 "$WORK/outputs"/lay_page_detect_run_*/lineage_*.jsonl  # 血缘首行 + 样本行
```

期望要点：

- 主成果一页一行，字段与交付说明数据集明细一致；
- 血缘首行 `record_type: task_lineage`，其后逐样本 `sample_lineage`；
- `review.jsonl` 的行带中文 `reviewReason` 与机器码 `code`。

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

# d) 算子参数非法（confidence_threshold 须在 (0, 1) 之间）
curl -s -X POST http://127.0.0.1:6288/predict -H "Content-Type: application/json" \
  -d '{"inputFile":"<上游 outputFile>","confidence_threshold":1.5}'
```

---

## 8. 复跑单元测试

```bash
cd <交付包根>
$PY -m pytest lay_page_detect/tests -q
```

期望：全部通过（4 / 4 通过；离线用例 mock 模型调用，不联网）。
