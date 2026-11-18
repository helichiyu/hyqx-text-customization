# 故障排查

## 1. 上传成功但没有部署

现象：

```text
zip 在服务器上
没有独立目录
没有容器
没有端口
```

原因：

- 上传只是文件传输，不会自动执行
- 自动部署平台没有触发
- 目标目录不是自动部署监听目录
- 自动部署要求特定文件名或结构

处理：

- 确认部署平台的触发方式
- 确认是否使用平台页面上传而不是 SFTP
- 确认是否要求 `docker-compose.yml`、`Dockerfile` 或清单文件
- 获得授权后手动解压并启动

## 2. 端口没有监听

```bash
ss -ltnp | grep ':17055'
docker ps -a --filter name=oppretrainRLpool
docker logs --tail=200 oppretrainRLpool
```

检查 Compose 端口、容器状态、启动命令和构建失败日志。

## 3. `/health` 不通

- 容器是否 running
- 健康检查端口是否与 Compose 一致
- 应用是否监听 `0.0.0.0`
- 防火墙是否允许访问
- 容器日志是否显示启动异常

## 4. 业务接口返回 401

原因：未发送入站令牌。

请求需要：

```http
X-Token: <原始令牌>
```

不是把 `AUTH_TOKEN_SHA256` 直接当令牌发送。

## 5. 业务接口返回 403

原因：发送的原始令牌与服务器摘要不匹配。

检查：

- 是否使用了正确的原始令牌
- 是否多个摘要用空格或逗号分隔
- `.env` 是否真正被容器加载
- 修改 `.env` 后是否重启或重建容器

## 6. `/docs` 打不开

这是正常现象。配置认证后会关闭 `/docs`、`/redoc`、`/openapi.json`。

使用仓库中的 API 文档或 OpenAPI 文件。

## 7. 模型网关连接失败

先从目标服务器验证 TCP：

```bash
timeout 5 bash -c '</dev/tcp/<gateway-host>/<gateway-port>' && echo OK || echo FAIL
```

如果 TCP 不通，接口返回再正确也无法调用模型。检查：

- VPN
- 防火墙
- 安全组
- 路由
- 代理
- 网关地址是否正确

## 8. 模型网关返回业务错误

检查：

- APPID
- APPKEY
- capability
- PATH 大小写和拼写
- `X-CurTime`
- `X-Server-Param`
- `X-CheckSum`
- 文本模型请求体和响应格式

签名头属于敏感信息，不要完整写入日志。

## 9. 数据丢失

不要执行：

```bash
docker compose down -v
```

不要删除命名数据卷。需要迁移时先备份卷，再验证。

## 10. 平台和服务器网络可达性

分别在平台 Pod 和目标服务器执行：

```bash
curl -v --max-time 15 http://<host>:<port>/health
```

本机能访问不代表平台能访问，反之亦然。

## 11. 长任务执行时 /health 超时

如果现象是：

```text
TCP 端口可连接
/health 请求 10-15 秒无响应
同时某个长耗时算子正在执行
```

原因通常不是网络，而是 FastAPI 事件循环被同步算子阻塞。

错误模式：

```python
@app.post("/predict")
async def predict(...):
    result = operator.run(...)  # 同步阻塞，占住事件循环
```

修复方式：把同步阻塞代码放到线程池：

```python
from starlette.concurrency import run_in_threadpool

@app.post("/predict")
async def predict(...):
    result = await run_in_threadpool(operator.run, input_path, output_path, context)
```

验收标准：

- 长任务执行期间 `/health` 仍能在 1 秒内响应
- 不应通过关闭健康检查或失败继续执行来绕过
- 并发请求不能共享可变的算子实例状态
- 必要时再由平台对同一实例做任务排队和限流
