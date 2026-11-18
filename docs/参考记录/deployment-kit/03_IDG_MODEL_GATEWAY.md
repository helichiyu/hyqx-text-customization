# IDG/磐智模型网关调用

## 认证方向

```text
平台 → 我方算子服务：X-Token
我方算子服务 → 模型网关：APPID + APPKEY + 签名头
```

二者不能混用。

## 请求头

```http
Content-Type: application/json
appKey: <APPKEY>
X-Server-Param: <base64-json>
X-CurTime: <unix-timestamp>
X-CheckSum: <md5>
```

生成逻辑：

```text
csid = APPID + capability.ljust(24, "0") + uuid
X-Server-Param = base64(json({"appid": APPID, "csid": csid}))
X-CheckSum = md5(APPKEY + X-CurTime + X-Server-Param)
```

## URL

```text
<gateway-base>/<model-path>
```

示例：

```text
/data-produce-1
/data-qwen35-2b-api
/data-qwen3.5-4b
/GLM-4-32B
/qwen3guard-gen-0.6b
/Qwen3-Embedding-0.6B/embeddings
```

PATH 必须严格按模型服务方提供的值使用，不要自行转换大小写或拼写。

## Chat 请求体

```json
{
  "model": "<model-name>",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "stream": false
}
```

## 响应

文本模型通常返回：

```json
{
  "choices": [
    {"message": {"content": "..."}}
  ]
}
```

检查响应头：

```text
X-Code 必须为空或 1000000
X-IsSync 不能为 false
```

Embedding 接口按 OpenAI 风格解析：

```json
{
  "data": [
    {"embedding": [0.1, 0.2]}
  ]
}
```

如果实际响应格式不同，需要在网关适配层转换。

## 示例文件

- `model_gateway/idg_signing_example.py`
- `model_gateway/README.md`

## 环境变量建议

```env
MODEL_PROVIDER=idg
MODEL_GATEWAY_BASE_URL=http://<gateway>:<port>
MODEL_APP_ID=<appid>
MODEL_APP_KEY=<appkey>
```

每个模型角色单独配置：

```env
POLICY_MODEL_NAME=<name>
POLICY_MODEL_PATH=<path>
```

## 安全

- APPKEY 只通过 Secret 或 `.env` 注入
- 不写入代码、Git、日志、错误消息
- 签名时间和随机数每次调用重新生成
- 生产链路必须使用 HTTPS
