# 算子服务部署工具包

本目录用于复用到其他产品，包含：

- 从发布包制作、上传、部署到验收的完整流程
- 镜像名、容器名、版本号和发布包命名规范
- FastAPI 入站认证拦截器
- IDG/磐智模型网关签名调用示例
- Docker Compose、Dockerfile、`.env` 和 deploy 脚本模板
- Windows 打包脚本和发布包安全检查
- 服务验收、模型连通性检查和回滚流程
- 发布检查表和故障排查

## 推荐阅读顺序

1. `01_UPLOAD_AND_DEPLOY_FLOW.md`
2. `02_AUTH_INTERCEPTOR.md`
3. `03_IDG_MODEL_GATEWAY.md`
4. `04_RELEASE_CHECKLIST.md`
5. `05_TROUBLESHOOTING.md`
6. `COT_MODEL_MAPPING.md`

## 关键原则

```text
上传成功 != 部署成功
镜像构建成功 != 服务可用
健康检查通过 != 模型调用可用
```

上传和部署是两个独立动作。未得到明确授权时，只允许上传和校验哈希，不得解压、构建镜像或重启容器。

## 命名规范

发布包和镜像使用小写短横线格式：

```text
oppretrain-sft-pool-v1.0.0.zip
oppretrain-sft-pool:1.0.0

oppretrain-eval-pool-v1.0.0.zip
oppretrain-eval-pool:1.0.0
```

容器名按平台约定配置，可以与镜像名不同。例如：

| 镜像 | 容器 |
|---|---|
| `oppretrain-sft-pool:1.0.0` | `oppretrainSFTpool` |
| `oppretrain-eval-pool:1.0.0` | `oppretrainEvalpool` |

## 标准交付结构

```text
product-name/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── inference.py
└── 应用代码/
```

真实 `.env`、APPKEY、API Key、服务器密码和 SSH 私钥不得进入发布包。

## 安全提醒

- `.env`、APPKEY、入站令牌、SSH 私钥不得提交到 Git
- 代码中禁止写死模型 API Key 或模型地址
- 模型接口配置必须通过环境变量或 Secret 注入
- 生产请求必须使用 HTTPS 或受控内网
- 上传包和镜像必须记录 SHA-256、镜像 ID 和版本号
- 回滚前不得删除旧镜像、旧目录或命名数据卷