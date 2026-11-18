# 发布检查表

## 一、命名与发布包

- [ ] 产品名使用小写短横线格式，例如 `oppretrain-sft-pool`
- [ ] 版本号已确定，例如 `1.0.0`
- [ ] 镜像名为 `<product-name>:<version>`
- [ ] 发布包名为 `<product-name>-v<version>.zip`
- [ ] 压缩包顶层目录为 `<product-name>/`
- [ ] 容器名、端口已和平台确认
- [ ] 压缩包内无 `.env`、Key、密码、私钥
- [ ] 压缩包内无 `runtime/`、`manual_data/`、缓存和测试产物
- [ ] `.env.example` 已包含全部必填变量和说明

## 二、发布前验证

- [ ] 代码编译通过
- [ ] 单元测试和关键链路测试通过
- [ ] 模型路由和签名测试通过
- [ ] 入站认证测试通过
- [ ] `docker compose --env-file .env.example -f docker-compose.yml config --quiet` 通过
- [ ] 镜像 tag 固定，不使用 `latest`
- [ ] 生产 `.env` 已在服务器准备，且不进入发布包
- [ ] 模型网关从目标服务器可访问
- [ ] 文本、Vision、Embedding 模型按需完成最小请求验证
- [ ] runtime 目录已挂载到持久化路径
- [ ] 日志轮转、健康检查和 `restart: unless-stopped` 已配置

## 三、上传

- [ ] 上传前已获得明确授权
- [ ] 发布包已上传到约定父目录
- [ ] 服务器 SHA-256 与本地一致
- [ ] 服务器文件大小正常
- [ ] 若仅授权上传，到此停止
- [ ] 未执行解压、构建或重启

## 四、部署

- [ ] 已获得部署授权
- [ ] 已记录旧镜像 ID、旧容器和旧目录
- [ ] 已确认回滚方式
- [ ] 解压后目录结构正确
- [ ] 生产 `.env` 已填写，无占位符
- [ ] Compose 配置检查通过
- [ ] 镜像名和 tag 正确
- [ ] 容器已启动
- [ ] 容器状态为 healthy
- [ ] 端口监听正常
- [ ] `/healthz` 返回 200 且 `code=0`
- [ ] 无令牌访问业务接口返回 401
- [ ] 正确 `X-Token` 访问返回 200
- [ ] 模型调用返回 `choices[0].message.content`
- [ ] Vision 输入验证通过（如适用）
- [ ] Embeddings 返回条数与输入一致（如适用）
- [ ] `/uploadFile -> /predict -> /downloadFile -> /removeFile` 冒烟通过
- [ ] 容器重建后 runtime 文件仍存在
- [ ] 日志中没有完整 Key、签名头和敏感原文

## 五、发布记录

- [ ] 已记录发布包 SHA-256
- [ ] 已记录镜像名、tag 和镜像 ID
- [ ] 已记录容器名、端口、数据卷和 runtime 目录
- [ ] 已记录模型路由和请求体 `model` 字段
- [ ] 已记录平台认证方式
- [ ] 已记录启动时间、执行人和验收结果
- [ ] 已保留旧版本，直到新版本验收完成

禁止执行：

```bash
docker compose down -v
```

`-v` 会删除命名数据卷和运行产物。