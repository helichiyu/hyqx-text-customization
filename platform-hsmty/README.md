# 文本定制化生产平台 · HSMTY 2.0.1 架构（tcs）

> 依据：`docs/前后端规范/新项目技术选型与环境复用框架_HSMTY对齐版.docx`（V2.0，2026-11-10）。
> 业务短名：`tcs`；前端模块名：`custom-text`。
>
> **本目录已包含完整业务迁移代码（后端 13 张表 + 5 大业务域，前端 6 个页面）；已按旧版逐页、逐接口完成功能对齐，核对结果见 `docs/旧版功能对齐核对.md`。原有 `platform/wbdz-server`、`platform/wbdz-web` 保持不动。**

---

## 1. 目录结构

```
platform-hsmty/
├─ tcs-server/                        # 后端聚合工程（hsmty-module-tcs-server）
│  ├─ pom.xml                         # 继承 com.hsmty:hsmty-module-starter:2.0.1
│  ├─ settings.xml.example            # 内网 Maven 配置模板（真实凭据不入库）
│  ├─ hsmty-module-tcs-client/        # 对外 Feign 契约、DTO、VO、降级实现
│  ├─ hsmty-module-tcs-core/          # Controller、Service、Mapper、PO、Liquibase
│  └─ hsmty-module-tcs-start/         # RunApplication、全局配置、application.yml、集成测试
├─ tcs-web/                           # 前端（Vue 3.5 / TS 5.9 / Vite 7 / Element Plus 2.14）
│  ├─ src/core/                       # 模块注册、鉴权适配、qiankun 生命周期、HTTP 封装
│  ├─ src/modules/custom-text/        # api / components / layout / stores / views / register.ts
│  │  ├─ views/                       # Workbench / TaskDetail / Material / Review / Dataset / Params
│  │  ├─ components/                  # BizIdText / PageHeader / SourcePreview / DatasetItemViewer
│  │  └─ layout/ModuleLayout.vue      # 侧边栏 + 多页签 + keep-alive
│  ├─ src/editions/obu.ts             # Cookie SSO 组合入口
│  └─ tests/                          # 模块注册测试
└─ deploy/                            # Docker、Nginx、K8s 清单
```

后端依赖方向固定为 `start → core → client`，`client` 不依赖 `core/start`，`core` 不依赖 `start`。

---

## 2. 技术基线

| 层次 | 版本 |
| --- | --- |
| 后端 | Java 21 / Spring Boot 4.0.9 / Spring MVC / 虚拟线程 |
| 公司基线 | `com.hsmty:hsmty-module-starter:2.0.1`（父链 `hsmty-boot-cloud` → `hsmty-build:2.0.1`，其 `spring-boot-starter-parent` 为 4.0.9；BOM 内 `spring-boot.version=4.0.6` 只作用于少数显式依赖） |
| ORM | MyBatis-Flex 1.11.7 + MyBatis + PageHelper |
| 数据库 | MySQL 8（默认）+ PostgreSQL（`-Ppostgresql`） |
| 迁移 | Liquibase（`changelog-master.xml` + 模块 changeset） |
| 缓存 | Redis Sentinel（`hsmty-common-db-redis`） |
| 鉴权 | UAP/SSO Cookie + Spring Security `@PreAuthorize`（不使用 JWT/BCrypt） |
| 服务调用 | Spring Cloud OpenFeign 4.1.3（`client` 模块契约） |
| 文件 | `hsmty-module-oss-client:2.0.1`（S3/MinIO） |
| 文档/监控 | springdoc-openapi 3.0.3 + Knife4j UI + Actuator |
| 前端 | Vue 3.5 / TypeScript 5.9 / Vite 7 / Element Plus 2.14 / Pinia 3 / Vue Router 5 |
| 前端工程 | Node 20.19.5 / pnpm 10.17.1 / qiankun 子应用 `custom-text` |
| 部署 | Docker + Nginx 1.28 + Kubernetes/Ingress |

端口与路径：后端 `8080`，上下文 `/hs-api`，模块前缀 `/hs-api/tcs`；Web 开发端口 `9848`，部署路径 `/sdom-hsmty/`。

---

## 3. 构建与运行

### 3.1 内网制品来源

`com.hsmty:*` 制品来自内网 Nexus：

```
http://192.168.1.110:13001/repository/maven-public/
```

- 该仓库同时代理 Maven Central，只读下载**不需要账号**；
- Gogs 仓库 `hsmty/hsmty-module-tcs-server` 自带的 `settings.xml` 指向同一 Nexus，其中 `localRepository` 是服务器路径 `/ruanjian/maven/repository`，Windows 本机不可用，**不要直接复用**；
- 本机做法：把 `tcs-server/settings.xml.example` 复制到仓库之外（例如 `C:\Users\<你>\.m2\hsmty-settings.xml`），只改 `localRepository`，Nexus 地址保持不变。**带凭据的 settings.xml 禁止入库。**

### 3.2 后端

前置：JDK 21（本机默认 `java` 可能是 8，需显式设置 `JAVA_HOME`）、Maven 3.9+、能访问上述 Nexus。

```bash
cd platform-hsmty/tcs-server
export JAVA_HOME=/path/to/jdk-21

# 首次构建：子模块 parent 的 relativePath 为空，父工程只能从仓库解析。
# 先把根工程（packaging=pom）装进本地仓库，非递归即可，无需注释 <modules>：
mvn -s /path/to/hsmty-settings.xml -N install
mvn -s /path/to/hsmty-settings.xml clean package
```

产物：`hsmty-module-tcs-start/target/hsmty-module-tcs-start.jar`（`finalName` 已固定为 artifactId）。

本地启动：

```bash
java -jar hsmty-module-tcs-start/target/hsmty-module-tcs-start.jar \
  --spring.liquibase.enabled=true
```

- 本机没有 Redis Sentinel 时，`redis.listener.enable: true` 会让启动失败（监听容器在启动阶段建连），本地验证可追加 `--redis.listener.enable=false`；
- 健康检查：`GET http://localhost:8080/hs-api/tcs/health`
- Actuator：`GET http://localhost:8080/hs-api/actuator/health`
- OpenAPI：`http://localhost:8080/hs-api/v3/api-docs`（生产用 `OPENAPI_ENABLED=false` 关闭）

### 3.3 前端

```bash
cd platform-hsmty/tcs-web
corepack enable
corepack prepare pnpm@10.17.1 --activate
pnpm install --frozen-lockfile
pnpm dev          # http://localhost:9848
pnpm type-check
pnpm test
pnpm lint
pnpm build        # 产物 dist/
```

### 3.4 部署

```bash
# 后端（需 BuildKit secret 注入内网 settings.xml）
docker build -f deploy/Dockerfile.server --secret id=maven_settings,src=settings.xml .

# 前端
docker build -f deploy/Dockerfile.web .

# K8s
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/tcs-server.yaml
kubectl apply -f deploy/k8s/tcs-web.yaml
kubectl apply -f deploy/k8s/ingress.yaml
```

---

## 4. 已完成与未完成

### 4.1 后端已完成

- `client / core / start` 三模块，依赖方向 `start → core → client`；POM 与内网模板对齐。
- 业务表 13 张（`db/changelog/tcs/001`～`013`）加初始参数版本（`014`）：任务、环节运行、素材批次/文件/变更、参数版本/草稿、复核单/条目、数据集/条目、交付记录、回滚记录；均带 `preConditions onFail="MARK_RAN"` 幂等保护。
- 初始参数数据：四条产线 + 公共规则各一份 `v1.0`（`014_tcs_param_version_seed.xml`），对应旧版 `DataSeeder`，保证新库可直接创建任务。
- 5 大业务域 Controller / Service / Mapper / PO / DTO / VO：
  - 素材：上传解包、准入校验（扩展名/大小/PDF 页数/HTML 可读性）、编辑、删除、校验、移交；
  - 任务：创建/编辑/提交/启动/驳回重跑/归集/阈值调整/删除、详情聚合（环节、产物、数据集、复核单）；
  - 复核：分页、详情、A/B/C 结论、撤销、数据集条目加入复核、整单闭环；
  - 数据集：分页、详情、发布、回滚、TXT 质量报告、交付记录；
  - 参数：产线概览、配置详情、草稿保存、版本发布。
- 任务编排：11 个算子按产线链式调用、3 次重试、阶段产物续链、进度回写、失败留痕。
- 算子文件契约：`/listFiles`、`/downloadFile`、`/progress` HTTP 读取（`file-mode=http`），本地可用 `local` 读共享目录；契约见 `docs/算子文件接口约定.md`。
- `@PreAuthorize` 权限码统一 `tcs:{resource}:{action}`；健康检查白名单开放。
- Long 序列化沿用框架策略；start 模块测试默认执行。

### 4.2 前端已完成

- qiankun 子应用骨架 + 模块自注册（`src/modules/custom-text/register.ts`）。
- 设计系统：`--tcs-*` 令牌、Element Plus 主题覆盖、页面/搜索/表格/弹窗/抽屉样式。
- 布局：顶栏 + 产线/公共管理侧边栏 + 多页签 + keep-alive。
- 页面：四条产线工作台、任务详情、素材管理、条件复核工作台、数据集管理、参数配置。
- API 层统一解包 `{code,message,data}`，分页参数 `page/limit` 转换，blob 预览/下载，错误统一提示。

### 4.3 待外部输入

- UAP/SSO 实际接入与本地放行规则（见 Q-005 / Q-007）。
- OSS/S3、生产数据库、Redis 实例参数。
- 菜单/字典号段与权限码清单落地。
- 算子侧按 `docs/算子文件接口约定.md` 实现三个文件接口并联调。

---

## 5. 与规范/文档的差异说明

| 项 | 处理 | 依据 |
| --- | --- | --- |
| 数据库名 | 本地开发用本地库 `tcs_db`；生产库上线前由运维创建，名称待定 | 2026-11-10 决策：新库在生产服务器建立，开发期用本地库；命名沿用《数据库开发通用规范》“库名以 `db` 结尾” |
| 模块前缀注册 | 已按内网模板实现 `ApiPrefixRegister` + `ApiPrefixProperties`，启动日志为 `Register API prefix module=tcs, prefix=/tcs` | 内网模板 `XxxApiPrefixConfiguration` / `ApiPrefixConfiguration` 实际代码 |
| 文档安全方案 | `Knife4jConfiguration` 不声明 Bearer/JWT；登录态由 UAP/SSO Cookie 承载 | 本文档 §5“不使用 JWT/BCrypt”；模板默认的 Bearer 方案不适用 |
| Liquibase 建表 | 拆为 `001`～`013` 共 13 个文件，逐表 `include`；模板遗留的空白 `001_tcs_init.xml` 已删除 | `CLAUDE.md` §9.2：每个表/每次结构变更单独文件，序号三位递增 |
| 算子调用 | 保持独立部署，平台按 HTTP 契约接入，不使用 Feign 内嵌算子；地址配置为“基地址 + 端口表” | 本文档 §7“算子独立部署、不内嵌 Python 运行时”；`operators/前后端对接说明.md` |
| Jackson 配置 | 不再自建 `JacksonConfiguration`，Long 精度处理交给 `hsmty-common-core` | 自建同名 Bean 会与框架冲突（`ConflictingBeanDefinitionException`）；框架策略为超安全整数转字符串 |
| 鉴权 | 前端不保存 Token、不解析 Cookie；登录态由主应用经 qiankun props 下发，后端以 `@PreAuthorize` 为最终边界 | 本文档 §3/§5/§6“UAP/SSO Cookie + Method Security” |
| 旧工程 | `platform/wbdz-server`、`platform/wbdz-web` 未改动 | 用户要求“升级代码放新文件夹，不覆盖原有代码” |

---

## 6. 验证状态

| 项 | 结果 |
| --- | --- |
| 前端 `pnpm install` | 通过（pnpm 10.17.1） |
| 前端 `pnpm type-check` | 通过 |
| 前端 `pnpm test` | 通过（2/2） |
| 前端 `pnpm lint` | 通过（0 error / 0 warning） |
| 前端 `pnpm build` | 通过（Element Plus 全量引入有 >500 kB chunk 警告，非错误） |
| 后端 `mvn -N install` | 通过（JDK 21.0.13 / Maven 3.9.11，本地仓库镜像） |
| 后端 `mvn clean package` | 通过（client / core / start 全部 SUCCESS，2026-11-11 复验） |
| 后端单元测试 | 通过（2/2：启动类注解、Long 序列化契约） |
| Liquibase | 本机 `tcs_db` 执行 14 个 changeSet（13 张表 + 初始参数），二次启动 `Run: 0`（幂等） |
| 后端启动 | 通过（`--redis.listener.enable=false`，本机无 Redis Sentinel） |
| 健康检查 | `GET /hs-api/tcs/health` → `200`，`{"code":"0000",...}` |
| 前端代理 | `GET http://localhost:9848/hs-api/tcs/health` → `200`（Vite → 8080） |
| 未登录接口 | `GET /hs-api/tcs/task` → `302`（UAP/SSO 未接入，见 Q-007） |

---

## 7. 需要甲方/公司提供

制品仓库已确认可用（§3.1），以下均为业务迁移前需要的信息：

1. UAP/SSO 接入信息：校验地址、跳转地址、Cookie 名称；本地是否需要放行（涉及关闭鉴权，需显式授权）。
2. OSS/S3：endpoint、bucket、AK/SK、上传/下载约定。
3. Redis Sentinel：master 名称、节点列表、密码（模板默认 `mymaster` / `192.168.1.102:26391-26393`）。
4. MySQL 8 / PostgreSQL 实例：生产地址、库名（本地开发暂用 `tcs_db`，生产库名待运维分配）、最小权限账号。
5. 菜单与权限码号段、字典来源号段。
6. qiankun 主应用注册信息：子应用名 `custom-text`、entry、挂载容器与用户/权限下发字段。
7. 算子侧：各算子宿主机地址、端口，以及 `docs/算子文件接口约定.md` 三个接口的实现与联调时间。

---

## 8. 后续接入顺序

1. 接入 UAP/SSO（或明确本地放行方式），打通前端登录态与 `@PreAuthorize`。
2. 生产库/Redis/OSS 参数到位后替换环境变量，执行 Liquibase 建表与字典/菜单初始化脚本。
3. 算子侧实现 `/listFiles`、`/downloadFile`、`/progress`，配置 `tcs.operator.base-url` 与端口表后联调整链。
4. 按主应用菜单体系调整 `register.ts` 的 `component` key，汇入总前端。
5. 确认无需旧数据后，下线 `platform/wbdz-*`。
