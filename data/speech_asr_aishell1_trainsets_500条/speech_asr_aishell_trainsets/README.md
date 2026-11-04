# AISHELL-1 抽取 500 条（S0002 + S0003，与 speech_asr_aishell1_trainsets 前 500 行一一对应）

## 目录结构与 CSV 路径完全一致

包解开后顶层目录就是 `speech_asr_aishell_trainsets`，因此 `speech_asr_aishell1_trainsets_前500条.csv` 里写的相对路径**可以直接当作文件路径使用，无需任何改动**：

```
speech_asr_aishell_trainsets/
├─ wav/train/S0002/           364 个 wav
├─ wav/train/S0003/           136 个 wav
├─ manifest.csv               对齐清单
├─ speech_asr_aishell1_trainsets_前500条.csv
└─ README.md
```

例如 CSV 第一行 `speech_asr_aishell_trainsets/wav/train/S0002/BAC009S0002W0122.wav`，
在包内就是同名相对路径的文件；用 `os.path.join(解包目录, csv 中的路径)` 即可直接打开。

## 来源

| 项目 | 说明 |
|---|---|
| 标注清单 | 魔搭 `speech_asr/speech_asr_aishell1_trainsets` |
| 音频 | HuggingFace 官方镜像 `AISHELL/AISHELL-1` → `data_aishell/wav/S0002.tar.gz`、`S0003.tar.gz` |
| 转写校验 | `data_aishell/transcript/aishell_transcript_v0.8.txt`（官方转写，逐条比对） |
| 许可 | AISHELL-1，Apache License 2.0（仅限学术研究，未经允许禁止商用） |

未下载 15.6 GB 的 `data_aishell.tgz` 整包，只取了包含目标文件的两个说话人分卷（36 MB + 40 MB）。

## manifest.csv 字段

| 字段 | 含义 |
|---|---|
| index | 在原 `speech_asr_aishell1_trainsets.csv` 中的行号（1 起，不含表头） |
| id | AISHELL 语音 ID，如 `BAC009S0002W0122` |
| speaker | 说话人（`S0002` / `S0003`） |
| csv_source_path | 原 CSV 中的相对路径 |
| local_file | 与 `csv_source_path` 完全相同，可直接用于打开文件 |
| text | 标注文本（按字空格分隔，与原 CSV 一致，仅去除行尾空格） |
| duration_sec | 时长（秒），由 wav 头解析 |
| sampling_rate / channels / bits | 16000 / 1 / 16 |
| size_bytes / sha256 | 文件大小与校验和 |
| transcript_verified | `yes` 表示与官方转写逐字一致 |

## 校验结果

- 500 行 CSV 全部找到对应音频，缺失 0；
- 包内路径与 CSV 相对路径逐条一致：500/500；
- 与官方转写逐条比对：**500/500 一致**，0 条不符；
- 说话人分布：S0002 364 条、S0003 136 条，顺序与原 CSV 前 500 行完全一致；
- 总时长 2453.3 秒（约 40.89 分钟），音频合计 74.89 MB；
- 全部为 16 kHz / 16 bit / 单声道。

## 用法示例

```python
import csv, os, wave
base = r"解包目录\speech_asr_aishell_trainsets"
rows = csv.DictReader(open(os.path.join(base, "speech_asr_aishell1_trainsets_前500条.csv"), encoding="utf-8"))
for r in rows:
    path = os.path.join(base, r["Audio:FILE"])       # 直接拼 CSV 里的路径
    with wave.open(path, "rb") as w:
        print(r["Audio:FILE"], w.getnframes() / w.getframerate(), r["Text:LABEL"])
```

需要更多数据时，按同一下载地址换 `S000x.tar.gz`（每个 25–45 MB）即可，新文件按同样层级放进 `wav/train/<spk>/` 就能被原 CSV 直接索引。
