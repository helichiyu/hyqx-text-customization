# 文本定制化生产平台 · 架构决策记录（tcs）

> 记录已确认的决策、依据和影响，避免后续会话重复讨论或无声偏离。
> 新决策追加编号 `D-00x`；推翻旧决策时保留原记录并标注"已废止 / 被 D-00x 替代"。
> 最后更新：2026-11-10

---

## 0. 文档优先级

| 优先级 | 文档 | 用途 |
| --- | --- | --- |
| 1 | `docs/前后端规范/新项目技术选型与环境复用框架_HSMTY对齐版.docx`（2026-11-10） | 架构、技术栈、目录、验收门禁的总依据 |
| 2 | `docs/前后端规范/CLAUDE.md` + 内网模板 `hsmty/hsmty-module-tcs-server` | 编码、分层、Liquibase、命名细则 |
| 3 | `docs/前后端规范/数据库开发通用规范.md` | **只取基础设施层面的通用约定**（字符集、时间、Redis 隔离、业务编号、菜单段位）；与 1/2 冲突处一律以 1/2 为准 |

仓库中未找到用户提到的 `新项目技术选型与环境复用框架_HSMTY对齐版(1).docx`，当前只有无后缀版本；如后续拿到 (1) 版，需先做差异比对再更新本文件。

---

## 1. 已确认决策

### D-001 服务边界：单服务 `tcs`

- **决策**：保持单个 `hsmty-module-tcs-server`（client / core / start），模块前缀 `/tcs`，不拆 PRE / PST。
- **依据**：2026-11-10 用户确认；本项目是"文本定制化生产"单一业务，不是文档 §4 描述的"统一 Web + PRE 预训练 + PST 后训练"多产线平台。
- **影响**：
  - 文档 §4 的 `pre/`、`pst/` 目录结构和 `PRE_SERVICE_URL` 不适用；
  - 业务模块在 `com.hsmty.tcs` 包内按 domain 划分，仍保持 client-core-start 边界与 `start → core → client` 依赖方向；
  - 若未来确需拆分，包名、artifactId、Feign 契约都要重做，成本较高。

### D-002 数据库：开发期用本地库，生产库上线前由运维创建

- **决策**：
  - 本地开发连接本机 MySQL，库名 `tcs_db`（`application.yml` 默认值）；
  - 生产库上线前在服务器上创建，库名、账号、权限由运维分配，届时只改 `TCS_DB_URL`；
  - 表结构仍由 Liquibase 脚本生成，手工建库只负责 `CREATE DATABASE`。
- **依据**：2026-11-10 用户确认"新库等生产时到服务器上建立，现在用本地库"；库名以 `db` 结尾取自《数据库开发通用规范》。
- **影响**：开发期不依赖内网数据库；`deploy/k8s/configmap.yaml` 中库名保留 `<db-name>` 占位。

### D-003 本地测试放宽，生产必须收紧

- **决策**：本地用 `local` profile 放行 UAP/SSO 校验，便于联调；生产环境必须接入真实 Cookie 校验，放行逻辑和测试凭据不入库。
- **依据**：2026-11-10 用户确认；文档 §11 第 5 步允许"本地放行逻辑使用 local profile 且不提交"。
- **影响**：`hsmty.verify` / `hsmty.redirect` 在本地可留空；生产由部署环境注入。当前启动日志出现 Spring Security 默认内存用户，属于尚未接入的真实状态，不作为验收结论。

### D-004 附录 A 的 SFT / EVAL / CoT / RLHF 不适用于本项目

- **决策**：不引入 `SFT_OPERATOR_BASE_URL`、`EVAL_OPERATOR_BASE_URL`、`COT_OPERATOR_BASE_URL`、`RLHF_OPERATOR_BASE_URL`。
- **依据**：2026-11-10 用户指出这些是后训练产线的配置；仓库 `operators/前后端对接说明.md` 显示本项目算子为 11 个、四条产线：
  - 文本元信息：`meta_clean_slice`(6301)、`meta_genre_judge`(6302)、`meta_fact_extract`(6303)、`meta_field_fill`(6304)
  - 复杂版面：`lay_page_render`(6305)、`lay_page_detect`(6306)
  - 公式文本：`fml_formula_locate`(6307)、`fml_formula_recognize`(6308)
  - 图文融合：`img_region_locate`(6309)、`img_type_classify`(6310)、`img_struct_describe`(6311)
- **影响**：算子配置应是"统一基地址 + 算子端口映射"（旧平台用 `WBDZ_OPERATOR_BASE` + `operator-ports` JSON），当前 `tcs.operator.base-url` 需要细化为基地址 + 端口表。

### D-005 《数据库开发通用规范》的取舍

- **决策**：只采纳基础设施层面的约定，数据库对象与 ORM 约定以 HSMTY 为准。
- **采纳**：
  - 字符集 `utf8mb4` / `utf8mb4_unicode_ci`；
  - 时间列用 `datetime`，不用 `timestamp`；
  - 不使用外键、不使用触发器/存储过程做业务逻辑；
  - 不使用 MySQL `json` 类型，JSON 存 `text` / `mediumtext`；
  - JDBC 串必须带 `characterEncoding=UTF-8` 与 `serverTimezone=Asia/Shanghai`；
  - 新项目使用独立 Redis db 号（现有系统占用 db3），连接信息向运维申请；
  - 对外业务编号 `前缀 + yyMMdd + 6 位随机码`，列建唯一索引，前缀先登记；
  - 菜单 ID 另起独立段位；
  - 密码用 Jasypt `ENC(...)`，主密钥走环境变量。
- **不采纳（与 HSMTY 冲突）**：

| 项 | 通用规范 | 采用（HSMTY） |
| --- | --- | --- |
| 表前缀 | `tb_` | `tcs_` |
| 审计列 | `creator/create_date/updater/update_date` | `create_id/create_time/update_id/update_time` |
| 逻辑删除 | `del_flag tinyint` 0/1 | `del_flag char(1)` `F`/`T` |
| 变更工具 | 手写 SQL + 人工执行，不用 Liquibase | Liquibase changeSet |
| ORM / 连接池 | MyBatis-Plus / Druid | MyBatis-Flex / Hikari |
| 主键 | MyBatis-Plus `ASSIGN_ID` | `SzIdGenerator` |

### D-006 算子接入：统一基地址 + 端口表，不内嵌 Python 运行时

- **决策**：`tcs.operator.base-url` + `tcs.operator.ports`（11 个算子）绑定到 `TcsOperatorProperties`，由 `TcsOperatorConfiguration` 注册；新增算子只追加端口，不改 Java 代码。
- **依据**：D-004；`operators/前后端对接说明.md` 与旧平台 `operator-ports` 配置形态。
- **影响**：未登记算子 `baseUrlOf` 返回空字符串，调用方按"不阻塞启动、调用失败返回稳定业务错误"处理；算子宿主机地址与端口均可由环境变量 `TCS_OPERATOR_BASE_URL` 覆盖（端口目前写死默认值，如部署变化需同步改 yml）。

### D-007 Long 序列化沿用框架策略，不自定义 JacksonConfiguration

- **决策**：删除本项目自建的 `com.hsmty.configuration.JacksonConfiguration`，Long 的 JSON 输出交给 `hsmty-common-core` 的 `com.hsmty.core.common.configuration.JacksonConfiguration`：超出 JS 安全整数（±9007199254740991）输出字符串，范围内输出数字。
- **依据**：启动时 `ConflictingBeanDefinitionException`（同名 Bean `jacksonConfiguration` 冲突）；反编译框架类确认已实现该策略，且比"全部 Long 转字符串"更合理（分页 total 等小数值保持数字）。
- **影响**：新增 `JacksonContractTest` 锁定框架行为；业务 VO 不需要再关心 Long 精度问题，**不要**在 start 模块再注册同名的 Jackson 配置类。

### D-008 start 模块显式开启测试

- **决策**：`hsmty-module-tcs-start/pom.xml` 设置 `<skipTests>false</skipTests>`，装配级/契约测试在 `mvn package` 时执行。
- **依据**：公司父工程默认 `skipTests=true`，仅删除 surefire 配置无效；不显式打开会导致"BUILD SUCCESS 但测试从未运行"。
- **影响**：当前 2 个测试（启动类注解、Long 序列化契约）纳入构建门禁；新增测试后必须确认 surefire 报告里确有执行记录。

---

## 2. 未决事项

| 编号 | 事项 | 需要谁定 | 当前倾向 |
| --- | --- | --- | --- |
| Q-001 | qiankun 菜单由子应用自注册，还是主应用统一下发（`component key` 映射） | 主应用（sdMainWeb）负责方 + 用户 | 子应用先自注册，主应用支持按 key 覆盖 |
| Q-002 | 算子文件传递方式：继续共享目录卷，还是改为 OSS 文件契约 | 用户 + 算子侧 | 文档禁止共享目录作为跨服务契约，长期应走 OSS；短期可保留卷 |
| Q-003 | 生产库名、账号、Redis db 号、S3 桶名 | 运维 | 按《数据库开发通用规范》申请 |
| Q-004 | 旧库 `wbdz_platform` 迁移方式与停机窗口 | 用户 | 停机一次性迁移 |
| Q-005 | UAP/SSO 地址、Cookie 名称、权限码清单 | 甲方/基座团队 | 待提供 |
| Q-006 | 首批业务实体与字段 | 用户/业务方 | 待提供，决定 `001_tcs_init.xml` |

---

## 3. 当前生效的工程约定（由上述决策推导）

- 后端单服务：`platform-hsmty/tcs-server`，上下文 `/hs-api`，模块前缀 `/tcs`，端口 8080。
- 本地库：`jdbc:mysql://127.0.0.1:3306/tcs_db`，字符集 `utf8mb4`。
- Redis：本地默认 db0；生产使用运维分配的独立 db 号。
- 鉴权：本地 `local` profile 放行；生产 UAP/SSO Cookie + `@PreAuthorize`。
- 算子：基地址 + 11 个算子端口映射，已实现为 `TcsOperatorProperties`（见 D-006）。
- JSON：Long 按 JS 安全整数策略序列化，由框架统一处理（见 D-007）。
- 构建：start 模块测试已开启，`mvn package` 会执行测试（见 D-008）。
- 迁移：Liquibase，`tcs_` 表前缀，`del_flag` 为 `F`/`T`。
