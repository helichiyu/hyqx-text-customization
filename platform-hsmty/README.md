# 文本定制化生产平台 · HSMTY 2.0.1 架构（tcs）

> 依据：`docs/前后端规范/新项目技术选型与环境复用框架_HSMTY对齐版.docx`（V2.0，2026-11-10）。
> 业务短名：`tcs`；前端模块名：`custom-text`。
>
> **本目录是架构升级骨架，不包含业务迁移代码；原有 `platform/wbdz-server`、`platform/wbdz-web` 保持不动。**

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
│  ├─ src/modules/custom-text/        # views / api / types / register.ts
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

### 4.1 已完成

- 后端 `client / core / start` 三模块骨架，POM 依赖清单与内网模板逐项对齐（含 `hsmty-common-feign`、`com.hsmty.excel:hsmty-common-excel`、MyBatis-Flex core/annotation/spring、`hsmty-common-db-mysql`/`-postgresql` profile、`spring-boot-starter-liquibase`、jasypt、aspectjweaver、`hsmty-module-oss-client`）。
- 模块前缀按模板真实机制实现：`core` 的 `TcsApiPrefixConfiguration` 注册 `ApiPrefixRegister`（`tcs` / `/tcs` / `com.hsmty.tcs.controller`），`start` 的 `ApiPrefixConfiguration` 用 `ApiPrefixProperties` + `WebMvcConfigurer` 生效。
- `com.hsmty.RunApplication`（排除服务发现/配置刷新，`AppVersionUtils` 输出版本横幅）、`Knife4jConfiguration`（因 Cookie SSO 不声明 Bearer 方案）。
- `application.yml`：8080、`/hs-api`、虚拟线程、MySQL/PostgreSQL profile、Liquibase、Redis Sentinel、springdoc、Actuator、模块前缀、白名单、Feign 地址（`tcs.service.url`、`oss.service.url`）、算子地址；环境变量可覆盖，敏感值不入库。
- Liquibase 主入口与模块汇聚入口；`001_tcs_init.xml` 已建立并挂载（无 changeSet，见 §5）。
- 健康检查接口 `/hs-api/tcs/health`（白名单开放）。
- 前端 `src/core`、`src/modules/custom-text`、`src/editions`、qiankun 生命周期、`createModuleHttp`、Pinia、Router 自动注册。
- Docker / Nginx / K8s 部署模板。

### 4.2 未完成（按迁移阶段推进）

- 业务表、字典、菜单、权限码、Liquibase changeSet。
- 业务 Controller / Service / Mapper / PO / DTO / VO。
- 素材、任务编排、复核、数据集、参数配置等页面。
- UAP/SSO 实际接入、OSS 实际读写、算子 HTTP/文件契约适配。
- 旧库 `wbdz_platform` → `sd_data_engineering` 的数据迁移。

---

## 5. 与规范/文档的差异说明

| 项 | 处理 | 依据 |
| --- | --- | --- |
| 数据库名 | 采用 `sd_data_engineering`，与 HSMTY 模板一致 | `CLAUDE.md` §12.4、模板 `README.md`“统一使用一个数据库”；旧库 `wbdz_platform` 迁移时再评估是否独立库 |
| 模块前缀注册 | 已按内网模板实现 `ApiPrefixRegister` + `ApiPrefixProperties`，启动日志为 `Register API prefix module=tcs, prefix=/tcs` | 内网模板 `XxxApiPrefixConfiguration` / `ApiPrefixConfiguration` 实际代码 |
| 文档安全方案 | `Knife4jConfiguration` 不声明 Bearer/JWT；登录态由 UAP/SSO Cookie 承载 | 本文档 §5“不使用 JWT/BCrypt”；模板默认的 Bearer 方案不适用 |
| `001_tcs_init.xml` | 已建文件并在模块 changelog 中 `include`，但**没有 changeSet** | 业务模型尚未迁移，凭空建表会把猜测固化成“已确认模型”；迁移首个实体时按 `CLAUDE.md` §9.2 补全 |
| 算子调用 | 保持独立部署，平台按 HTTP 契约接入，不使用 Feign 内嵌算子 | 本文档 §7“算子独立部署、不内嵌 Python 运行时” |
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
| 后端 `mvn -N install` | 通过（JDK 21.0.13 / Maven 3.9.11 / 内网 Nexus） |
| 后端 `mvn clean package` | 通过（client / core / start 全部 SUCCESS） |
| 后端启动 | 通过（`--redis.listener.enable=false`，本机无 Redis Sentinel） |
| 健康检查 | `GET /hs-api/tcs/health` → `200`，`{"code":"0000",...}` |
| OpenAPI 分组 | `GET /hs-api/v3/api-docs` → `200`，包含 `/tcs/health` |

---

## 7. 需要甲方/公司提供

制品仓库已确认可用（§3.1），以下均为业务迁移前需要的信息：

1. UAP/SSO 接入信息：校验地址、跳转地址、Cookie 名称、local profile 放行规则。
2. OSS/S3：endpoint、bucket、AK/SK、上传/下载约定。
3. Redis Sentinel：master 名称、节点列表、密码（模板默认 `mymaster` / `192.168.1.102:26391-26393`）。
4. MySQL 8 / PostgreSQL 实例：地址、库名（默认 `sd_data_engineering`）、最小权限账号。
5. 菜单与权限码号段、字典来源号段。
6. 旧库 `wbdz_platform` 数据迁移范围与窗口。
7. qiankun 主应用注册信息：子应用名 `custom-text`、entry、挂载容器与用户/权限下发字段。

---

## 8. 迁移建议顺序

1. 按业务域迁移 Liquibase 建表（补全 `001_tcs_init.xml`）→ PO/Mapper → Service/Controller → DTO/VO。
2. 按 `src/modules/<domain>/register.ts` 迁移页面与 API，先打通 `custom-text` 模块。
3. 接入 UAP/SSO、OSS 与算子契约，补齐权限码与菜单。
4. 完成旧库数据迁移与新库双写/切换方案后，再下线 `platform/wbdz-*`。
