# ID 引用兼容说明

## 1. 对外引用

- 任务详情新链接统一使用业务编号：`/task/<bizNo>`。
- 复核入口新链接统一使用业务编号查询参数：`/review?orderBizNo=<bizNo>`。
- 列表、详情和抽屉中的业务编号统一使用 `BizIdText` 等宽展示并提供复制按钮。
- 新页面链接不包含内部 Long ID。

## 2. 迁移期兼容

- 前端新链接只生成 bizNo。
- `TaskController`、`MaterialController`、`ReviewController`、`DatasetController` 的路径变量统一命名为 `reference`。
- `reference` 为纯数字时按内部 Long ID 解析；否则按 bizNo 查询。
- 四个 Controller 额外提供 `/by-no/{bizNo}` 详情查询入口。
- 旧的 `/task/<Long>`、复核 `orderId` 查询参数和旧内部 ID API 在迁移期继续可用。

## 3. 业务编号规则

- 格式：2–4 位大写字母前缀 + `yyMMdd` + 6 位安全随机码。
- 安全字符集：`23456789ABCDEFGHJKMNPQRSTUVWXYZ`，共 31 个字符。
- 随机源：`SecureRandom`（CSPRNG）。
- 落库场景使用 `BizId.nextUnique`，最多执行 8 次碰撞重试。
- Task、Dataset、Review、Material、Delivery、Rollback 均有 bizNo 唯一约束。

## 4. 内部主键策略

- MyBatis-Flex `flexId` 当前为 18 位正 Long，趋势递增且唯一。
- 内部 Long ID 仅用于数据库关联、编排和内部调用，不作为新页面链接。
- 当前离 19 位边界仍有充足空间，本轮不强制补位或迁移历史主键。
- 后续如规范强制 19 位，应单独设计主键迁移、新旧兼容读取和唯一性校验。

## 5. 验证

- `BizIdTest` 覆盖格式、安全字符集、非法前缀、10,000 次唯一性和碰撞重试/耗尽。
- `InternalIdTest` 覆盖 flexId 正 Long、当前 18 位和唯一性。
- `LogicDeleteIntegrationTest` 覆盖 bizNo/Long 双引用解析。
- `TaskControllerTest` 覆盖新 bizNo 路径和旧 Long 路径兼容。