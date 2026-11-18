# 算子服务上传与生产部署流程

本文用于其他产线复用，覆盖从发布包制作、上传、校验、解压、启动、验收到回滚的完整流程。

核心原则：

```text
上传成功 != 部署成功
镜像构建成功 != 服务可用
健康检查通过 != 模型调用可用
```

上传和部署是两个独立动作。未得到明确授权时，只允许上传文件和校验哈希，不得解压、构建镜像或重启容器。

---

## 1. 命名规范

### 1.1 发布包和镜像

统一使用小写短横线格式：

```text
<product-name>-v<version>.zip
<product-name>:<version>
```

示例：

```text
oppretrain-sft-pool-v1.0.0.zip
oppretrain-sft-pool:1.0.0

oppretrain-eval-pool-v1.0.0.zip
oppretrain-eval-pool:1.0.0
```

要求：

- `product-name` 全部小写，单词之间使用 `-`。
- 版本号使用 `主版本.次版本.修订版本`，例如 `1.0.0`。
- 同一版本对应同一镜像，不允许修改代码后继续复用旧 tag。
- 建议同时记录镜像 ID 和发布包 SHA-256。

### 1.2 容器名称

容器名称按平台约定配置，可以使用驼峰格式，但必须与镜像名区分清楚。

示例：

| 产品 | 镜像 | 容器 | 端口 |
|---|---|---|---|
| SFT 指令微调 | `oppretrain-sft-pool:1.0.0` | `oppretrainSFTpool` | `17054` |
| 评测语料 | `oppretrain-eval-pool:1.0.0` | `oppretrainEvalpool` | `17057` |

Compose 中示意：

```yaml
services:
  oppretrain-sft-pool:
    image: oppretrain-sft-pool:${SFT_IMAGE_TAG:-1.0.0}
    container_name: oppretrainSFTpool
```

---

## 2. 标准发布包结构

压缩包顶层必须包含一个独立项目目录，避免污染共享父目录：

```text
product-name/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── inference.py
└── 应用代码/
```

压缩包名称：

```text
product-name-v1.0.0.zip
```

解压后的结构：

```text
/data/webapp/idg/新数据工程产线算子/
└── product-name/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── .env
    └── ...
```

### 2.1 必须包含

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- 依赖清单
- 应用代码和算子配置
- 必要的运行期静态数据
- 健康检查说明
- 回滚说明或部署记录

### 2.2 禁止包含

- `.git/`
- `.pytest_cache/`
- `__pycache__/`
- `runtime/`
- `outputs/`
- `manual_data/`
- `datasets_external/`
- 本地测试数据和大文件
- 真实 `.env`
- APPKEY、API Key、SSH 私钥
- 明文服务器账号密码
- 不必要的压缩包、日志和临时目录

`.env.example` 可以随包交付；真实 `.env` 必须单独在服务器上生成或通过安全渠道下发。

---

## 3. 发布前检查

### 3.1 代码检查

```bash
python -m compileall -q .
```

运行单元测试和关键链路测试，至少覆盖：

- 健康检查
- 入站认证
- 模型路由和签名
- 单条异常隔离
- 文件上传、预测、下载、删除
- 过滤、失败和重试路径

### 3.2 Compose 检查

```bash
docker compose --env-file .env.example -f docker-compose.yml config --quiet
```

检查内容：

- 镜像名和 tag
- 容器名
- 端口映射
- `restart: unless-stopped`
- `healthcheck`
- runtime 持久化目录
- 日志轮转
- 认证变量
- 模型网关变量

### 3.3 发布包检查

```powershell
Get-FileHash -Algorithm SHA256 .\product-name-v1.0.0.zip
```

同时扫描压缩包，确认：

- 没有 runtime、manual_data、缓存和测试产物
- 没有真实 Key、密码和私钥
- 顶层目录名与产品名一致
- `.env.example` 存在，真实 `.env` 不存在

### 3.4 模型配置检查

生产环境不允许在代码中写死模型地址、Key 或测试模型。

推荐变量：

```env
MODEL_PROTOCOL=panzhi
MODEL_GATEWAY_BASE_URL=http://<gateway>:<port>
MODEL_APP_ID=<appid>
MODEL_APP_KEY=<appkey>
LLM_TIMEOUT_SECONDS=600
LLM_MAX_CONCURRENCY=1
```

每个调用模型的算子必须独立配置路由和请求体 `model` 字段：

```env
<OPERATOR>_MODEL_PATH=/<exact-route>
<OPERATOR>_API_MODEL=<exact-model-field>
```

路由和模型字段必须严格照模型清单或接口方 demo 填写，不能自行转换大小写、补前缀或猜测。

---

## 4. 上传发布包

目标目录示例：

```text
/data/webapp/idg/新数据工程产线算子
```

上传命令：

```powershell
scp -P <port> .\product-name-v1.0.0.zip <user>@<host>:"/data/webapp/idg/新数据工程产线算子/"
```

上传完成不等于部署完成。此阶段只完成文件传输。

### 4.1 服务器校验

```bash
cd '/data/webapp/idg/新数据工程产线算子'
sha256sum product-name-v1.0.0.zip
ls -lh product-name-v1.0.0.zip
```

服务器 SHA-256 必须与本地完全一致。

如果用户只授权上传，到此停止，不得执行后续步骤。

---

## 5. 解压和部署

执行前再次确认：

- 已获得部署授权
- 已备份旧目录或旧镜像
- 已确认目标端口未被占用
- 已确认 `.env` 已准备好
- 已确认模型网关从目标服务器可达

### 5.1 备份旧版本

部署前记录：

```bash
docker ps -a --filter name=<container-name>
docker images <product-name>
docker inspect <container-name> --format '{{.Image}}'
```

保留旧镜像和旧项目目录，直到新版本验收完成。

### 5.2 解压

```bash
cd '/data/webapp/idg/新数据工程产线算子'

unzip -l product-name-v1.0.0.zip
unzip product-name-v1.0.0.zip
```

解压前确认目标目录不会覆盖其他产品。若同名目录已存在，先确认旧版本备份和回滚方式。

### 5.3 配置生产环境

```bash
cd product-name
cp .env.example .env
vi .env
```

必须填写：

```env
MODEL_GATEWAY_BASE_URL=...
MODEL_APP_ID=...
MODEL_APP_KEY=...
AUTH_REQUIRED=1
AUTH_TOKEN_SHA256=...
<产品端口变量>=...
<runtime 目录变量>=...
```

检查：

```bash
docker compose --env-file .env -f docker-compose.yml config --quiet
```

真实 `.env` 不得回传、不得提交 Git、不得写入日志。

### 5.4 构建和启动

```bash
docker compose --env-file .env -f docker-compose.yml up -d --build
```

如果镜像必须在其他环境构建，应先在允许的构建节点完成，再通过镜像仓库分发，不应在生产服务器临时安装大量依赖。

启动后检查：

```bash
docker compose ps
docker ps --filter name=<container-name>
docker logs --tail=200 <container-name>
```

---

## 6. 验收流程

### 6.1 健康检查

```bash
curl -fsS http://127.0.0.1:<port>/healthz
```

要求：

- HTTP 200
- 返回 `code=0`
- 容器状态为 healthy
- 长任务执行期间健康检查仍能快速响应

### 6.2 端口检查

```bash
ss -lntp | grep ':<port>'
```

平台访问源和服务器本机都要分别测试；本机能访问不代表平台能访问。

### 6.3 入站认证检查

未带令牌：

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  http://127.0.0.1:<port>/
```

预期：`401`

带正确令牌：

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "X-Token: <token>" \
  http://127.0.0.1:<port>/
```

预期：`200`

健康检查路径必须不需要令牌。

### 6.4 模型调用检查

必须从算子容器内部发起，而不是只在宿主机测试。

文本模型：

```bash
curl -fsS -X POST '<gateway>/<route>' \
  -H 'Content-Type: application/json' \
  -H 'appKey: <appkey>' \
  -H 'X-CurTime: <time>' \
  -H 'X-Server-Param: <param>' \
  -H 'X-CheckSum: <checksum>' \
  -d '{"model":"<model>","messages":[{"role":"user","content":"只回复OK"}],"stream":false}'
```

验收要求：

- HTTP 2xx
- `X-Code` 为空或 `1000000`
- `X-IsSync` 不是 false
- 响应存在 `choices[0].message.content`
- 请求体 `model` 字段与接口方要求完全一致

图片模型必须额外验证 Vision 输入，Embedding 模型必须额外验证 `/embeddings` 和向量条数。

### 6.5 算子冒烟测试

至少执行一次：

```text
/uploadFile -> /predict -> /downloadFile -> /removeFile
```

检查：

- 主输出文件存在
- `outputFilePath` 可被下一算子读取
- 拒绝样本和失败记录正确落盘
- 运行时文件位于持久化目录
- 容器重建后历史目录仍在
- 日志中没有完整 Key、签名头和用户敏感原文

---

## 7. 发布记录

| 项目 | 内容 |
|---|---|
| 产品名 |  |
| 版本 | `1.0.0` |
| 镜像名 |  |
| 镜像 ID |  |
| 容器名 |  |
| 端口 |  |
| 发布包路径 |  |
| 发布包 SHA-256 |  |
| 目标服务器 |  |
| 共享父目录 |  |
| 独立项目目录 |  |
| runtime 持久化目录 |  |
| 模型网关 |  |
| 模型路由/字段 |  |
| 入站认证 |  |
| 启动时间 |  |
| 健康检查 |  |
| 认证检查 |  |
| 模型检查 |  |
| 算子冒烟测试 |  |
| 回滚镜像/目录 |  |
| 执行人 |  |

---

## 8. 回滚流程

回滚前确认旧镜像和旧目录仍存在。

```bash
docker compose down
docker images <product-name>
```

恢复旧目录或旧 `.env` 后启动旧镜像：

```bash
docker compose up -d
```

禁止使用：

```bash
docker compose down -v
```

`-v` 会删除数据卷，导致历史产物丢失。

回滚后重新执行健康检查、认证检查和一个最小算子请求。

---

## 9. 常见问题

### 9.1 上传成功但没有部署

原因：上传只是文件传输，不会自动解压或启动容器。

处理：确认是否有部署平台触发机制；没有明确授权时不要自行解压和启动。

### 9.2 容器运行但端口不通

检查：

```bash
docker ps -a --filter name=<container-name>
docker logs --tail=200 <container-name>
ss -lntp | grep ':<port>'
```

同时检查防火墙、安全组和端口占用。

### 9.3 健康检查失败

检查：

- 健康检查路径是否为实际的 `/healthz`
- 应用是否监听 `0.0.0.0`
- 容器内部端口是否与 Compose 一致
- 长任务是否阻塞事件循环
- 是否因为缺少认证变量导致服务启动失败

### 9.4 业务接口 401/403

- 401：没有携带 `X-Token`
- 403：令牌与 `AUTH_TOKEN_SHA256` 不一致
- 不要把摘要本身当令牌发送

### 9.5 模型调用失败

逐项检查：

1. 网关地址和端口
2. APPID、APPKEY
3. 路由
4. 请求体 `model`
5. capability 和签名
6. `X-Code`
7. `X-IsSync`
8. 是否从容器内部可达

### 9.6 容器重建后文件消失

原因：输出目录没有挂载到宿主机或命名卷。

处理：把算子 runtime 根目录统一指向持久化目录，例如：

```env
SFT_RUNTIME_ROOT=/data/runtime
```

并在 Compose 中挂载：

```yaml
volumes:
  - "/data/webapp/idg/新数据工程产线算子/runtime:/data"
```

### 9.7 镜像非常大或构建很慢

如果模型由独立模型服务器提供，生产镜像不应再安装 `torch`、`transformers` 或携带模型权重。应制作远程模型专用轻量镜像，并缓存基础依赖层。

---

## 10. 最终验收清单

- [ ] 发布包名称符合规范
- [ ] 镜像名和 tag 符合规范
- [ ] 容器名和端口符合规范
- [ ] 压缩包顶层目录正确
- [ ] 本地和服务器 SHA-256 一致
- [ ] 无 `.env`、Key、密码和私钥
- [ ] 无 runtime、manual_data 和缓存
- [ ] Compose 配置检查通过
- [ ] 模型网关容器内可达
- [ ] 文本、Vision、Embedding 按需验证
- [ ] 健康检查通过
- [ ] 401/200 认证检查通过
- [ ] 上传、预测、下载、删除通过
- [ ] runtime 重建后仍存在
- [ ] 日志无敏感信息
- [ ] 旧版本和回滚方式已记录
- [ ] 生产变更已获得明确授权