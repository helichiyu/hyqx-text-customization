# 模板使用说明

1. 复制 `Dockerfile.template` 到产品目录并改名为 `Dockerfile`
2. 复制 `docker-compose.template.yml` 并改名为 `docker-compose.yml`
3. 复制 `.env.template` 并改名为 `.env`
4. 按产品修改端口、容器名、数据卷、模型环境变量
5. 复制 `deploy.sh` 到产品目录
6. 运行 `docker compose config --quiet` 检查
7. 用 `tools/build_release.ps1` 打包
8. 上传 zip 并检查是否自动部署

`.env.template` 中的值必须全部替换，不能把占位符带上生产。


## 不同产线必须调整的接口参数

每个产品在 `.env` 中明确自己的健康检查和业务查询路径：

```env
HEALTH_PATH=/health
OPERATORS_PATH=/operators
REQUIRE_AUTH=1
AUTH_WHITELIST_PATHS=/health,/healthz
```

CoT 示例：`HEALTH_PATH=/healthz`、`OPERATORS_PATH=/functions`。
