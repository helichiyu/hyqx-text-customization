# 文本定制化生产平台 · 平台端

平台端由两部分组成：

| 目录 | 内容 | 技术栈 |
| --- | --- | --- |
| `wbdz-server/` | 业务后端：素材、任务编排、条件复核、数据集、参数配置、鉴权 | Spring Boot 3.5.4 / Java 21 / MyBatis-Flex / Liquibase / MySQL 8 |
| `wbdz-web/` | 管理前端：四条产线工作台 + 公共管理 | Vue 3.5 / TypeScript / Vite 6 / Element Plus 2.9 |

算子服务（11 个）在仓库根 `operators/`，交付包在 `release/`，接口契约见 `operators/前后端对接说明.md`。

---

## 1. 本地启动

### 1.1 前置

- JDK 21（本项目验证用 `C:/Dev/jdk-21.0.13+9`）
- Maven 3.9+
- Node.js 18+（含 npm）
- MySQL 8（本机 3306，库 `wbdz_platform`；首次启动由 Liquibase 自动建表/初始化）
- Python 3.12（仅本地直跑算子时需要，见第 3 节）

### 1.2 后端

```bash
cd platform/wbdz-server

# 数据库连接可用环境变量覆盖（默认 127.0.0.1:3306 / root / wbdz123）
export WBDZ_DB_HOST=127.0.0.1
export WBDZ_DB_PORT=3306
export WBDZ_DB_USER=root
export WBDZ_DB_PASSWORD=wbdz123

# 算子产物根目录：须与算子进程的 OUTPUT_DIR 指向同一位置
export WBDZ_OP_RUNTIME_DIR=E:/data

mvn -DskipTests spring-boot:run
```

服务起于 `http://127.0.0.1:8090`，健康检查 `GET /api/healthz`。
种子账号：`admin / admin123`。

> Maven 自身也必须运行在 JDK 21 上（`JAVA_HOME` 指向 JDK 21），否则
> `spring-boot-maven-plugin` 会报 class file version 61.0 不兼容。

### 1.3 前端

```bash
cd platform/wbdz-web
npm install
npm run dev     # http://localhost:5173，/api 代理到 127.0.0.1:8090
```

生产构建：

```bash
npm run build   # 产物 dist/，由 Nginx 托管并反代 /api
```

---

## 2. 配置项

后端配置在 `wbdz-server/src/main/resources/application.yml`，均可用环境变量覆盖：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `WBDZ_DB_HOST` / `WBDZ_DB_PORT` | `127.0.0.1` / `3306` | MySQL 地址 |
| `WBDZ_DB_USER` / `WBDZ_DB_PASSWORD` | `root` / `wbdz123` | 数据库账号（生产必须更换） |
| `WBDZ_JWT_SECRET` | 内置开发密钥 | JWT 签名密钥（生产必须更换） |
| `WBDZ_JWT_EXPIRE_HOURS` | `72` | 登录有效期 |
| `WBDZ_STORAGE_DIR` | `./wbdz-storage` | 上传素材落盘目录 |
| `WBDZ_OP_RUNTIME_DIR` | `./op-runtime` | 算子产物根（平台读取阶段 zip/产物文件） |
| `WBDZ_OPERATOR_BASE` | `http://127.0.0.1` | 算子服务地址前缀 |
| `wbdz.operator-ports`（yml 内联） | 6301–6311 | 11 个算子的宿主机端口映射 |

前端开发代理在 `wbdz-web/vite.config.ts`，默认 `5173 → 8090`。

---

## 3. 算子服务与硅基流动配置

算子服务可二选一启动：

**A. Docker（交付形态，需要 Docker）**

```bash
cd release
for f in *.zip; do unzip -q "$f" -d "${f%.zip}"; done
docker compose up -d --build     # 11 个服务，宿主机端口 6301–6311
```

**B. 本地进程（本项目验证方式，不需要 Docker）**

```bash
# 项目根执行；依赖已装在 .venv（Python 3.12）
export MSYS2_ENV_CONV_EXCL='INPUT_DIR;OUTPUT_DIR'   # Git Bash 下防止路径被改写
export INPUT_DIR=/data/input                          # Windows 上解析为 <当前盘>:\data\input
export OUTPUT_DIR=/data/output
PY="E:/HYQX/文本定制化生产/.venv/Scripts/python.exe"
for pair in meta_clean_slice:6301 meta_genre_judge:6302 meta_fact_extract:6303 \
            meta_field_fill:6304 lay_page_render:6305 lay_page_detect:6306 \
            fml_formula_locate:6307 fml_formula_recognize:6308 \
            img_region_locate:6309 img_type_classify:6310 img_struct_describe:6311; do
  tag=${pair%%:*}; port=${pair##*:}
  (cd operators/$tag && INPUT_DIR=/data/input OUTPUT_DIR=/data/output PORT=$port \
     nohup "$PY" -I -m uvicorn inference:app --host 127.0.0.1 --port $port > /tmp/$tag.log 2>&1 &)
done

# 健康检查
for p in $(seq 6301 6311); do curl -s http://127.0.0.1:$p/healthz; echo; done
```

本地进程方式下，`INPUT_DIR/OUTPUT_DIR` 的 `/data/...` 在 Windows 上落到当前盘根
（如 `E:\data\input`），后端须设置 `WBDZ_OP_RUNTIME_DIR=E:/data` 才能读取产物。

### 3.1 模型密钥与网关

模型统一走硅基流动（OpenAI 兼容接口），配置在算子包内
`<算子>/<算子>/utils/llm_config.py`：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SILICONFLOW_BASE_URL` | `https://api.siliconflow.cn/v1` | 可替换为私有网关 / 代理地址 |
| `SILICONFLOW_API_KEY` | 内置交付密钥 | 生产必须改为环境变量注入，不写进镜像/仓库 |
| `VISION_MODEL` | `Qwen/Qwen3-VL-32B-Instruct` | 视觉类算子模型 |
| `TEXT_MODEL` | `deepseek-ai/DeepSeek-V3.2` | 文本类算子模型 |

给 11 个算子进程统一注入即可，例如 Docker compose 的 `environment`，或本地启动前 `export`。
内置密钥仅用于联调；正式交付前应轮换，并通过 `SILICONFLOW_API_KEY` 覆盖。

---

## 4. 现场验证脚本

`platform/scripts/` 下是本次联调使用的驱动脚本（需项目根 `.venv`，内含 requests）：

| 脚本 | 作用 |
| --- | --- |
| `e2e_lines.py [line...]` | 四条产线：上传 → 校验 → 移交 → 建任务 → 提交 → 启动 → 轮询到待复核 |
| `e2e_finish.py` | 复核结论（A/B/C）→ 闭环 → 归集 → 发布 → 质量报告下载 → 回滚 |
| `e2e_regress.py` | 状态机与门禁回归（13 项） |
| `uitest/walkthrough.js` | Edge 无头走查：登录 + 10 个页面截图 + 控制台错误收集 |
| `uitest/viewer_check.js` | 数据集明细查看抽屉：页图/框选图层加载与错误收集 |

```bash
cd <项目根>
.venv/Scripts/python.exe -I platform/scripts/e2e_lines.py metadata layout formula graphic
.venv/Scripts/python.exe -I platform/scripts/e2e_finish.py
.venv/Scripts/python.exe -I platform/scripts/e2e_regress.py
cd platform/scripts/uitest && node walkthrough.js <taskId> <reviewOrderId>
```

---

## 5. 关键技术约定

- **主键**：18 位雪花 ID；JSON 响应统一序列化为字符串（`JacksonConfig`），前端按不透明字符串使用，避免 JS 精度丢失。
- **逻辑删除**：`del_flag`（F 正常 / T 删除），业务代码不物理删除。
- **审计字段**：`create_by/create_time/update_by/update_time` 由 `AuditListener` 统一填充。
- **算子路径**：算子回 `/data/...`；本地直跑回 Windows 绝对路径，`OperatorClient.toHostPath` 两种形态都校验并落在 `op-runtime` 根内。
- **复核机器码**：算子 `review/skipped/failed` 条目带 `code`，平台写入复核单 `triggerCode` 与条目 `code`；中文 `reason` 仅展示。
- **质量报告**：按交付说明 §十模板输出（生成时间 / 版本 / 来源任务 / 内容条数 / 复核处置 / 数据范围），仅含处理信息与质量结论，不含原始数据；复核处置按有效复核单条目统计，作废单不计入。
