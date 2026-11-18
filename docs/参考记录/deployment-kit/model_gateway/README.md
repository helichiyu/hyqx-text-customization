# IDG 示例说明

运行前设置环境变量：

```powershell
$env:MODEL_APP_ID = "<appid>"
$env:MODEL_APP_KEY = "<appkey>"
$env:MODEL_GATEWAY_BASE_URL = "http://<gateway>:<port>"
python .\idg_signing_example.py
```

脚本会：

1. 生成 `X-CurTime`
2. 生成 csid
3. 生成 base64 编码的 `X-Server-Param`
4. 计算 `X-CheckSum`
5. 调用模型 PATH
6. 检查 `X-Code` 和 `X-IsSync`
7. 读取 `choices[0].message.content`

不要把真实 APPKEY 写进脚本。
