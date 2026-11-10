# hsmty-module-xxx-server 开发规范

> 适用范围：`hsmty-module-xxx-server` 及其派生的所有业务服务端模块。
> 文中 `xxx` 为业务短名占位符，`Xxx` 为其大驼峰形式；落地到具体业务时按第 1.2 节一次性替换，**不得保留 `xxx` / `Xxx` / `charging` / `充电站` 等模板残留**。
> 本规范依据仓库当前代码与 `README.md` 整理；与 `README.md` 冲突时以本规范为准，并同步修正 README。

---

## 1. 约定与占位符

### 1.1 模块命名

| 模块    | artifactId                  | 职责                                                           |
| ----- | --------------------------- | ------------------------------------------------------------ |
| 客户端模块 | `hsmty-module-{xxx}-client` | 对外服务契约：Feign 接口、DTO、VO、降级实现。供**其它服务**依赖                        |
| 核心模块  | `hsmty-module-{xxx}-core`   | 业务实现：Controller、Service、Mapper、PO、模块配置、Liquibase 变更脚本       |
| 启动模块  | `hsmty-module-{xxx}-start`  | 唯一可执行模块：启动类、全局配置、`application.yml`、Liquibase 主入口、集成测试 |

- 根工程 `hsmty-module-xxx-server`：`packaging=pom`，父工程为 `com.hsmty:hsmty-module-starter`，通过 `revision` 统一版本（当前 `2.0.1`），不写业务代码。
- 三个子模块 POM 的 `<parent><relativePath/></parent>` 为空，即**父工程从 Maven 仓库解析**，本地首次构建必须先把根工程 `install` 到本地仓库（见第 12 节）。

### 1.2 业务名替换对照

| 模板值                                                       | 替换为                     | 示例（业务 = `order`）      |
| --------------------------------------------------------- | ----------------------- | --------------------- |
| `xxx`（artifactId、包名、目录、模块前缀、表前缀、字典来源、权限前缀）                | 业务短名，小写字母               | `order`               |
| `com.hsmty.xxx`                                           | `com.hsmty.` + 业务短名     | `com.hsmty.order`     |
| `Xxx` / `XxxEntity` / `XxxController` 等                    | 业务名大驼峰                  | `Order` / `OrderEntity` |
| `xxx管理`、`充电站`、`ChargingStation` 等注释与文案                   | 实际业务对象名称                | `订单管理` / `订单`          |
| `xxx_table`（模板表名）                                        | `{业务短名}_{对象}`           | `order_main`          |
| `705500000000000001`（菜单号段样例）                              | 本业务独立号段                 | `705600000000000001`  |

模板中的 `001_xxx_init.xml` 当前是**空白文件**，落地时必须按第 9.2 节补全建表脚本。

---

## 2. 整体架构

```
                 ┌──────────────────────────────┐
   其它业务服务 ──▶│  hsmty-module-xxx-client      │  只发布契约
                 │  feign / pojo(dto,vo)         │
                 └──────────────┬───────────────┘
                                │ 被 core 依赖
                 ┌──────────────▼───────────────┐
                 │  hsmty-module-xxx-core        │  业务实现，无启动类
                 │  controller / service /       │
                 │  mapper / pojo / config       │
                 └──────────────┬───────────────┘
                                │ 被 start 依赖
                 ┌──────────────▼───────────────┐
                 │  hsmty-module-xxx-start       │  唯一可执行模块
                 │  RunApplication / 全局配置 /   │
                 │  application.yml / changelog  │
                 └──────────────────────────────┘
```

### 2.1 依赖方向（强约束）

- `start` → `core` → `client`，**禁止反向依赖**。
- `client` 不得依赖 `core`、`start`，不得引入 `spring-boot-starter-web` 等运行期容器组件。
- `core` 不得依赖 `start`。
- `core` 中 Web 相关依赖必须声明为 `provided` + `optional`（当前已有：`spring-boot-starter-web`、`spring-web`、`spring-webmvc`、`jakarta.servlet-api`），新增同类依赖同样处理。
- 任何业务模块都不得被 `hsmty-common-*` 反向依赖。
- 跨服务调用只能通过 `client` 中的 Feign 契约，禁止在 `core` 中自行编写 HTTP 客户端或依赖其它服务的 `core`。

### 2.2 技术栈

| 类别       | 选型                                                                                                   |
| -------- | ---------------------------------------------------------------------------------------------------- |
| 语言       | Java 21（`maven.compiler.source/target=21`，可用虚拟线程、record、文本块、模式匹配）                                         |
| 基础框架     | Spring Boot / Spring MVC（版本由 `hsmty-module-starter` 统一管理）、Spring Cloud OpenFeign 4.1.3                |
| 公共能力     | `hsmty-common-core`、`hsmty-common-log`、`hsmty-common-db-core`、`hsmty-common-db-redis`、`hsmty-common-security`、`hsmty-common-excel` |
| ORM      | MyBatis-Flex（主）+ MyBatis + PageHelper                                                                  |
| 数据库变更    | Liquibase                                                                                            |
| 鉴权       | Spring Security 方法级鉴权（`@PreAuthorize`，由 `hsmty-common-security` 提供的统一安全体系支撑）                               |
| Excel    | FastExcel（`cn.idev.excel`）+ `hsmty-common-excel`                                                       |
| 接口文档     | springdoc-openapi + Knife4j UI，生产环境通过配置关闭                                                              |
| 配置加密     | Jasypt（`ENC(...)`），敏感值不得明文入库                                                                           |
| 其它       | Lombok、FreeMarker（代码生成）、yauaa（User-Agent 解析）、Actuator                                             |

---

## 3. 各模块职责

### 3.1 `hsmty-module-xxx-client`（客户端模块）

1. 只放被外部消费的契约：Feign 接口、降级工厂/降级实现、DTO、VO。
2. 不放 Controller、Service、Mapper、Entity、`@Configuration`、数据库/Redis 相关实现。
3. 已发布接口的删除、改名、字段类型变更属于**破坏性变更**，必须评估所有调用方；新增字段默认兼容。
4. 所有 DTO/VO 字段必须带 `@Schema`；时间字段按需加 `@DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")`。
5. 当前 POM 中 `skipTests=true`，client 模块不写测试。

### 3.2 `hsmty-module-xxx-core`（核心模块）

1. 承接全部业务逻辑、数据访问、模块级配置与 REST 接口。
2. Controller 入参使用 client 模块的 DTO，出参使用 client 模块的 VO，**禁止在 core 再建同名契约类**。
3. 不写 `main` 方法、不引 `spring-boot-maven-plugin`，保持普通 jar。
4. 模块级配置统一放 `com.hsmty.xxx.config`（API 前缀、MapperScan），不要外溢到 start。
5. Liquibase 变更脚本放 `resources/db/changelog`，由 start 的主 changelog 挂载。
6. 依赖 `hsmty-module-common` 提供跨业务共享契约；新增依赖前确认是否已有公共封装。

### 3.3 `hsmty-module-xxx-start`（启动模块）

1. 只放启动类、跨模块/全局配置、`application.yml`、Liquibase 主入口、集成测试，不写业务逻辑。
2. 启动类 `RunApplication` 必须位于 `com.hsmty` 根包，保证组件扫描与 `@EnableFeignClients` 覆盖 `com.hsmty.**`。
3. 全局配置类统一放 `com.hsmty.configuration`（当前为 `ApiPrefixConfiguration`、`Knife4jConfiguration`）。
4. 数据库驱动通过 Maven profile 选择：`mysql`（默认）/ `postgresql`，禁止在 `core` 写死驱动坐标。
5. 启动类 Banner 使用 `System.out.println` 属于唯一例外，业务代码禁止使用。

---

## 4. 包结构与用途

> 三个模块共用根包 `com.hsmty.xxx`，按功能拆分子包；`xxx` 为业务短名。

### 4.1 client 模块

```
com.hsmty.xxx
├── feign
│   ├── XxxFeignClient.java
│   ├── fallback/XxxFeignClientFallbackFactory.java
│   └── impl/XxxFeignClientImpl.java
└── pojo
    ├── dto/{XxxCreateDTO, XxxUpdateDTO, XxxListDTO}.java
    └── vo/XxxVO.java
```

| 包                        | 用途       | 要点                                                                 |
| ------------------------ | -------- | ------------------------------------------------------------------ |
| `...feign`               | 出站调用契约   | `@FeignClient` 的 `name` 为逻辑服务名、`contextId` 必填且唯一、`url` 指向配置项 |
| `...feign.fallback`      | 熔断降级工厂   | 实现 `FallbackFactory<T>`，`@Component`，记录 `cause` 后返回降级实现             |
| `...feign.impl`          | 降级默认值    | 返回空集合/空对象，不抛异常、不伪造业务数据                                             |
| `...pojo.dto`            | 入参       | 创建/修改/查询三类；查询 DTO 必须 `extends PageQuery`                          |
| `...pojo.vo`             | 出参       | 可含冗余展示字段（如 `provinceName`），不得直接暴露 PO                              |

### 4.2 core 模块

```
com.hsmty.xxx
├── config
│   ├── XxxApiPrefixConfiguration.java   # 注册模块 API 前缀
│   └── XxxMapperScanConfiguration.java  # 只扫描本模块 mapper 包
├── controller/XxxController.java
├── service
│   ├── XxxService.java
│   └── impl/XxxServiceImpl.java
├── mapper/XxxMapper.java
└── pojo
    ├── po/XxxEntity.java
    └── excel/XxxExcel.java
```

| 包                            | 用途     | 要点                                                                                  |
| ---------------------------- | ------ | ----------------------------------------------------------------------------------- |
| `...config`                  | 模块级配置  | `ApiPrefixRegister` 声明 `module/prefix/basePackages`；`@MapperScan` 只扫本模块，避免多模块互扫           |
| `...controller`              | REST 入口 | 只做接收参数 → 调 Service → 包装返回，不写业务判断、不直接访问 Mapper                                       |
| `...service`                 | 业务接口   | 继承 `IService<Entity>`，方法按 `create/update/remove/page/list/detail` 命名                  |
| `...service.impl`            | 业务实现   | 继承 `ServiceImpl<Mapper, Entity>`；事务、校验、转换、远程编排都在这里                                     |
| `...mapper`                  | 数据访问   | 继承 `BaseMapper<Entity>`；简单查询用 `QueryWrapper`，复杂 SQL 才写 XML                         |
| `...pojo.po`                 | 数据库实体  | 与表一一对应，仅用于持久化，不得直接作为接口入参/出参                                                        |
| `...pojo.excel`              | Excel 模型 | `@ExcelProperty` / `@ExcelIgnore` / `@DictFormat`，与 VO 分离                            |

### 4.3 core 资源目录

| 路径                                                       | 用途                                                                    |
| -------------------------------------------------------- | --------------------------------------------------------------------- |
| `src/main/resources/mapper/xxx/XxxMapper.xml`            | Mapper XML；`namespace` 与接口全限定名一致，必须提供 `BaseResultMap` 与 `Base_Column_List` |
| `src/main/resources/db/changelog/xxx/NNN_xxx_{desc}.xml` | 本业务 Liquibase 变更文件，序号三位递增，每个表/每次结构变更单独一个文件                            |
| `src/main/resources/db/changelog/module-xxx-changelog.xml` | 模块 changelog 汇聚入口，新增变更文件后在此 `include`                                   |

### 4.4 start 模块

```
com.hsmty
├── RunApplication.java
└── configuration
    ├── ApiPrefixConfiguration.java   # 聚合各模块 ApiPrefixRegister
    └── Knife4jConfiguration.java     # OpenAPI 基础信息与 Bearer 安全方案
```

| 路径                                              | 用途                                                                    |
| ----------------------------------------------- | --------------------------------------------------------------------- |
| `resources/application.yml`                     | 全局配置（端口、数据源、Redis、MyBatis-Flex、Jasypt、文档、鉴权白名单、Feign 地址）              |
| `resources/db/changelog/changelog-master.xml`   | Liquibase 主入口，`include` 各模块 `module-xxx-changelog.xml`（`errorIfMissing="false"`） |
| `resources/region/ip2region_v4.xdb`             | 离线 IP 地域库，二进制文件禁止转换换行符（见 `.gitattributes`）                             |
| `src/test/resources/logback-test.xml`           | 测试日志配置；当前模板尚无测试类                                                      |

---

## 5. 命名规范

### 5.1 类命名

| 类型         | 规则                                                                     | 示例                              |
| ---------- | ---------------------------------------------------------------------- | ------------------------------- |
| Controller | `{主体}Controller`                                                       | `XxxController`                 |
| Service    | `{主体}Service` / `{主体}ServiceImpl`                                       | `XxxService` / `XxxServiceImpl` |
| Mapper     | `{主体}Mapper`                                                           | `XxxMapper`                     |
| 实体         | `{主体}Entity`，包名 `pojo.po`                                              | `XxxEntity`                     |
| 入参         | `{主体}CreateDTO` / `{主体}UpdateDTO` / `{主体}ListDTO`                      | —                               |
| 出参         | `{主体}VO`                                                               | `XxxVO`                         |
| Excel      | `{主体}Excel`                                                            | `XxxExcel`                      |
| Feign      | `{主体}FeignClient` / `{主体}FeignClientFallbackFactory` / `{主体}FeignClientImpl` | —                               |
| 配置         | `{主体}ApiPrefixConfiguration` / `{主体}MapperScanConfiguration`（core）      | 全局配置放 `configuration` 包          |

### 5.2 接口路径与权限码

- 基础路径 = `server.servlet.context-path`（`/hs-api`）+ 模块前缀（`/xxx`）+ Controller `@RequestMapping`。
- Controller 上的 `@RequestMapping` 写**资源名**（小写），不要重复写 `/hs-api` 或模块前缀；前缀由 `XxxApiPrefixConfiguration` 统一注册。
  - 模板中模块前缀与 Controller 路径同为 `xxx` 仅为占位；落地示例：模块 `charging` + `@RequestMapping("station")` → `/hs-api/charging/station`。
- 权限码与 `@PreAuthorize`、菜单 `permissions`、初始化脚本三处保持一致：
  - 单资源业务：`{业务}:{动作}`，如 `xxx:create`。
  - 多资源业务：`{业务}:{资源}:{动作}`，如 `xxx:user:create`。
  - 动作固定为 `create` / `update` / `remove` / `page` / `detail`（模板 Controller 实际使用这五个）。
- 开放接口（白名单）必须同步加入 `router.whitelist` 并在变更说明中注明。

### 5.3 数据库命名

- 表名：`{业务模块}_{对象}` 的 `snake_case`，所有业务表必须带模块前缀，如 `xxx_item`、`xxx_item_detail`、`xxx_item_rel`。
  - 前缀与 artifactId、包名、Liquibase 目录一致，不得缩写或使用通用词。
  - 禁止 `user`、`order`、`device`、`config` 等无前缀表名，防止跨模块重名与迁移冲突。
  - 关联表、明细表、扩展表、临时表同样遵守；平台公共表（`sys_dict`、`sys_menu` 等）由 `hsmty-common-*` 维护，业务模块**不得创建或修改**。
- 列名：`snake_case`；Java 字段驼峰，依赖 `map-underscore-to-camel-case: true` 映射。
- 字典类型：`{业务模块}_{资源}_{字段}`，如 `xxx_item_status`；字典项 `alias` 用小写下划线（如 `in_use`）。
- 菜单 ID、字典来源号段：每个业务独占，不得复用其它业务号段。

---

## 6. 分层开发规范

### 6.1 Controller

```java
@Tag(name = "xxx管理")
@RestController
@RequestMapping("xxx")
@RequiredArgsConstructor
public class XxxController {

    private final XxxService xxxService;

    @Operation(summary = "新增xxx")
    @PreAuthorize("hasAnyAuthority('xxx:create')")
    @PostMapping
    public ApiResult<Void> create(@RequestBody XxxCreateDTO dto) {
        xxxService.create(dto);
        return ApiResult.success();
    }

    @Operation(summary = "查询xxx列表")
    @PreAuthorize("hasAnyAuthority('xxx:page')")
    @GetMapping
    public ApiResult<PageResult<XxxVO>> list(XxxListDTO dto) {
        return ApiPageResult.success(xxxService.page(dto));
    }
}
```

要求：

1. 类上必须有 `@Tag`、`@RestController`、`@RequestMapping`、`@RequiredArgsConstructor`。
2. 每个方法必须有 `@Operation(summary = ...)` 与 `@PreAuthorize`；白名单接口必须显式说明原因。
3. 返回值统一：无数据 `ApiResult.success()`；单对象 `ApiResult.success(vo)`；分页 `ApiPageResult.success(pageResult)`；禁止直接返回 PO 或自由 JSON。
4. 方法体只做“接收 → 调 Service → 包装返回”，禁止业务判断，禁止访问 Mapper。
5. HTTP 语义：新增 `POST`、修改 `PUT`、删除 `DELETE`（批量删除用 `@RequestBody SelectIdsDTO`）、分页/列表 `GET` + `ListDTO`、详情 `GET /{id}`。
6. 分页接口签名固定为 `ApiResult<PageResult<XxxVO>>`，查询 DTO 继承 `PageQuery`。
7. 参数校验使用 `jakarta.validation` 注解（`@NotBlank`、`@NotNull` 等），配合 `@Valid` / `@Validated`。

### 6.2 Service / ServiceImpl

```java
public interface XxxService extends IService<XxxEntity> {
    void create(XxxCreateDTO dto);
    void update(XxxUpdateDTO dto);
    void remove(SelectIdsDTO dto);
    PageResult<XxxVO> page(XxxListDTO dto);
    List<XxxVO> list(XxxListDTO dto);
    XxxVO detail(Long id);
}
```

要求：

1. 接口继承 `IService<Entity>`，实现继承 `ServiceImpl<Mapper, Entity>`；通用 CRUD 直接复用父类方法。
2. 方法命名固定为 `create / update / remove / page / list / detail`；其它业务动作按动词命名（`publish`、`revoke` 等）。
3. 校验与断言使用 `CommonResponseEnum`：
   ```java
   CommonResponseEnum.INVALID_ID.assertTrue(dto.getIds().isEmpty()); // 条件为 true 时抛出
   CommonResponseEnum.INVALID_ID.assertNull(xxxEntity);              // 对象为空时抛出
   ```
4. DTO ↔ PO、PO ↔ VO 转换统一用 `BeanCopyUtils.copy(source, Target.class)`，禁止手写大段 `setXxx`。
5. 分页统一 `PageUtils.getPage(dto)` / `PageUtils.getPageResult(page)`；查询用 `pageAs(...)`，列表用 `listAs(...)`。
6. 查询条件集中写在私有 `buildQueryWrapper(XxxListDTO dto)` 中；非空判断用 `Utils.isNotNull(...)`，空集合判断用 `ObjectUtil.isEmpty(...)`。
7. 依赖注入统一**构造器注入**：`@RequiredArgsConstructor` + `private final`；新增代码禁止 `@Autowired` 字段注入（模板中 Feign 字段注入属于待收敛的遗留写法，见第 16.2 节）。
8. 跨服务数据通过 client 的 Feign 获取，并对空结果判空（降级实现返回空集合）。
9. 涉及多表/多步写操作的方法加 `@Transactional(rollbackFor = Exception.class)`。
10. 控制器与 Service 均不直接操作 Redis，缓存统一走 `RedisCache`。

### 6.3 Mapper

1. 继承 `com.mybatisflex.core.BaseMapper<XxxEntity>`，不加 `@Mapper`（由 `@MapperScan` 注册）。
2. 简单查询全部使用 `QueryWrapper`；仅多表关联、复杂聚合、数据库函数才写 XML。
3. XML 必须提供 `BaseResultMap` 与 `Base_Column_List`，新增字段同步更新两处。
4. Mapper 中禁止业务判断。

### 6.4 PO（Entity）

```java
@Data
@Table(value = "xxx_table", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "xxx对象")
public class XxxEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    private Long id;

    // 业务字段...

    @Column(isLogicDelete = true)
    @Schema(description = "删除标记")
    private String delFlag;
}
```

要求：

1. 必须 `implements Serializable` 并声明 `serialVersionUID`。
2. 主键固定 `Long` + `@Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)`，禁止自增或手动赋值。
3. `@Table` 必须挂 `onInsert/onUpdate = EntityChangeListener.class`，由框架填充创建人、创建时间、更新人、更新时间，业务代码**不要手写这四个字段**。
4. 通用字段固定：`id`、`createId`、`createTime`、`updateId`、`updateTime`、`delFlag`。
5. **禁止物理删除**：删除一律逻辑删除；`delFlag` 标 `@Column(isLogicDelete = true)`，正常值 `"F"`、删除值 `"T"`（全局配置）。
6. 每个字段必须带 `@Schema(description = ...)`；金额、经纬度等精确值用 `BigDecimal`。
7. 状态类字段用 `String` 存字典 `alias`，禁止魔法数字。
8. `@Table(value = "...")` 的表名必须是 `{业务模块}_{对象}`，与 Liquibase 建表脚本、Mapper XML 完全一致；模板的 `xxx_table` 必须替换。

### 6.5 DTO / VO / Excel

1. 三者职责分离，不得混用：DTO 只接收、VO 只返回、Excel 只负责导入导出。
2. 所有字段带 `@Schema`；查询 DTO 继承 `PageQuery`。
3. 字段校验使用 `jakarta.validation` 注解。
4. 新增/修改 DTO 不暴露 `createId/createTime/updateId/updateTime/delFlag` 等审计字段；VO 可以暴露。
5. Excel 模型：导出字段 `@ExcelProperty(value = "列名")`，主键等不导出字段 `@ExcelIgnore`，字典字段 `@DictFormat(dictType = "...")`，需要显示名称时加 `useAlias = true`（如模板中的 `charging_station_status` 必须替换为实际字典类型）。

---

## 7. 接口与鉴权规范

1. 统一返回结构：

   | 场景     | 返回                                  |
   | ------ | ----------------------------------- |
   | 无数据成功  | `ApiResult.success()`               |
   | 单对象    | `ApiResult.success(vo)`             |
   | 列表     | `ApiResult.success(list)`           |
   | 分页     | `ApiPageResult.success(pageResult)` |

2. 业务异常通过 `CommonResponseEnum` 或统一异常体系抛出，由全局异常处理器转换为标准响应；Controller 内禁止 `try/catch` 后自行拼响应。
3. 鉴权基于 Spring Security 方法级注解 `@PreAuthorize("hasAnyAuthority('...')")`；权限值必须与菜单数据一致，不要自行实现权限判断。
4. 白名单配置在 `application.yml` 的 `router.whitelist`；新增开放接口必须同步登记。
5. 文档注解完整：Controller `@Tag`、方法 `@Operation`、字段 `@Schema`；生产环境通过 `springdoc.swagger-ui.enabled` / `springdoc.api-docs.enabled` 关闭入口。
6. 新增 Controller 包必须注册到本模块 `ApiPrefixRegister`，否则不会自动带模块前缀。

---

## 8. 服务间调用规范

1. 调用方只依赖 `hsmty-module-xxx-client`，通过注入 Feign 接口调用；不得依赖被调方 `core`。
2. Feign 接口模板（以仓库实际配置为准）：

   ```java
   @FeignClient(name = "hsmty-xxx-server", url = "${xxx.service.url}", contextId = "XxxFeignClient",
       fallbackFactory = XxxFeignClientFallbackFactory.class, configuration = FeignConfig.class)
   public interface XxxFeignClient {

       @Operation(summary = "根据 ID 批量查询")
       @PostMapping("/xxx")
       List<XxxVO> getByIdList(@RequestBody Collection<Long> idList);
   }
   ```

   要求：

   - `name` 为逻辑服务名；`contextId` 唯一且与接口名对应。
   - 地址通过 `application.yml` 的 `{业务}.service.url` 配置（仓库当前为 `xxx.service.url`），本项目排除了服务发现自动配置，**真实地址只来自该配置项**，禁止写死 IP。
   - 必须指定 `fallbackFactory` 与 `configuration = FeignConfig.class`。
   - 请求路径必须与提供方实际暴露的路径一致（包含 context-path 与模块前缀），联调时以 `/hs-api/{模块}/...` 校验。
   - 模板中 `getByIdList` 使用 `Collection<?>` 且摘要为“查询行政区域详情”，属于占位残留，落地时改为 `Collection<Long>` 与实际摘要。
3. 降级工厂记录 `cause` 后返回 `XxxFeignClientImpl`；降级实现返回空集合/空对象，不伪造业务数据，调用方必须判空。
4. 批量接口优先（`getByIdList` 模式），避免循环单条远程调用。
5. Feign 接口是跨服务契约：只增不改；字段类型与语义变更必须与所有调用方同步发布。
6. 模块 client 中的 Feign 用于**其它服务调用本服务**；若本模块需要调用第三方/其它业务，应注入被调方提供的 client，不要在本模块 client 中自引用。

---

## 9. 数据访问与数据库变更规范

### 9.1 ORM 约定

- 主 ORM 为 MyBatis-Flex；`map-underscore-to-camel-case: true`，PO 字段用驼峰。
- `auto-mapping-unknown-column-behavior: none`：结果集出现 PO 未声明的列会报错，改表后必须同步 PO。
- 逻辑删除全局值：删除 `"T"`、正常 `"F"`；新增表 `del_flag` 默认 `'F'`、类型 `char(1)`。
- 优先使用 `BaseMapper` / `IService` 方法：`save`、`saveOrUpdate`、`getById`、`removeByIds`、`pageAs`、`listAs`。
- PageHelper 配置见 `application.yml` 的 `page-helper`，分页参数统一走 `PageUtils`。

### 9.2 Liquibase 变更规范

1. 文件位置：`hsmty-module-xxx-core/src/main/resources/db/changelog/{业务}/NNN_{业务}_{描述}.xml`，序号三位递增：
   ```
   db/changelog/xxx/001_xxx_init.xml
   db/changelog/xxx/002_xxx_dict_init.xml
   db/changelog/xxx/003_xxx_menu_init.xml
   db/changelog/xxx/004_xxx_item_add_column.xml
   ```
2. 每个模块必须有汇聚入口 `module-xxx-changelog.xml`，新增文件后在其中 `include`；入口文件只增不删。
3. 主入口 `start/src/main/resources/db/changelog/changelog-master.xml` 统一挂载模块入口：
   ```xml
   <include file="db/changelog/module-xxx-changelog.xml" errorIfMissing="false"/>
   ```
4. `changeSet` 规范：
   - `id`：`{业务}-{动作}-{对象}-{yyyyMMdd}`，全项目唯一；**已执行的 changeSet 禁止修改**，变更必须新增 changeSet。
   - `author`：真实提交人。
   - `context`：需要兼容两种数据库时写 `mysql,postgresql`。
   - 必须写 `preConditions onFail="MARK_RAN"` 做幂等：
     - 建表：`<not><tableExists tableName="..."/></not>`
     - 加列：`<not><columnExists tableName="..." columnName="..."/></not>`
     - 初始化数据：`<sqlCheck expectedResult="0">SELECT COUNT(*) ...</sqlCheck>`
   - 表名必须带业务模块前缀；只允许操作本模块表，禁止跨模块改表。
   - 表、列必须写 `remarks`；主键 `bigint`、非空约束显式声明。
5. 初始化顺序：字典来源/类型/项 → 菜单与权限按钮 → 业务数据，单独文件、单独 changeSet。
6. `spring.liquibase.enabled` 默认 `false`，按环境显式开启；生产环境严禁修改历史 changeSet 的 checksum，应新增变更或使用 `changelogSync`。
7. 当前 `001_xxx_init.xml` 为空文件，落地时必须补全建表脚本，并与 `XxxEntity` 字段、`XxxMapper.xml` 的 `BaseResultMap` 三处一致。

### 9.3 数据初始化号段

| 内容                     | 规则                                          | 样例                |
| ---------------------- | ------------------------------------------- | ----------------- |
| 字典来源 `sys_dict_source` | 每个业务独立号段                                    | 样例 `3000-3999`    |
| 字典类型 `sys_dict_type`   | 使用本业务号段起始 ID                                | `3000`            |
| 字典项 `sys_dict`         | `类型ID * 1000 + 序号`                          | `3000001`         |
| 菜单/按钮 `sys_menu`       | 每业务独立 18 位号段，权限码与 `@PreAuthorize` 一致        | 样例 `7055...`      |

新增业务必须申请新号段，禁止复用其它业务号段。

---

## 10. 配置规范

1. 统一配置在 `start/src/main/resources/application.yml`，按 `---` 分块：`server/spring` → `springdoc` → `mybatis-flex/page-helper` → `hsmty` → `jasypt` → `router` → `{业务}.service.url`。
2. 环境相关值（数据库、Redis、Feign 地址、密钥）必须可通过环境变量/配置中心覆盖，**不得在代码中写死**。
3. 敏感信息禁止明文提交：数据库/Redis 密码使用 Jasypt `ENC(...)`；Jasypt 主密码（当前模板为 `datasource`）仅限本地调试，生产必须通过环境变量注入并更换算法/密钥。
4. 模块 API 前缀双处保持一致：
   - 代码：`XxxApiPrefixConfiguration`（`module`、`prefix`、`basePackages`）。
   - 配置：`hsmty.api-prefix.modules.xxx`（`enabled`、`prefix`），配置项优先于代码默认值。
5. 端口与上下文路径：当前为 `server.port: 8080`、`server.servlet.context-path: /hs-api`；新增模块不得自行修改全局值。
6. springdoc 分组：`group-configs[0].group` 与 `packages-to-scan` 必须同步为新业务包 `com.hsmty.xxx`；模板中 `operations-sorter: alpha·` 含多余字符，落地时修正为 `alpha`。
7. Liquibase：`change-log: classpath:db/changelog/changelog-master.xml`，`enabled: false`（按环境开启）。
8. 已启用虚拟线程（`spring.threads.virtual.enabled: true`）；阻塞式远程调用必须配置合理超时，避免长时间占用。
9. 新增配置项优先使用 `@ConfigurationProperties` 绑定并提供默认值，避免散落 `@Value`。
10. 统一数据库名称为 `sd_data_engineering`（见 README），不得为单模块另建库；多模块共用同一库、按表前缀隔离。

---

## 11. 公共工具与依赖复用（README 约定）

优先复用下列公共能力，**不要重复造轮子**；新增工具前先确认 `hsmty-common-*` 是否已有实现。

| 工具 / 封装                                              | 用途                      |
| ---------------------------------------------------- | ----------------------- |
| `cn.hutool.core.util.ObjectUtil`                     | 空对象、空集合判断               |
| `com.hsmty.core.common.entity.ApiResult`             | 统一接口返回                  |
| `com.hsmty.core.common.entity.ApiPageResult` / `PageResult` | 分页返回与分页结果               |
| `com.hsmty.core.util.DateUtils`                      | 日期时间操作                  |
| `com.hsmty.redis.RedisCache`                         | 缓存操作（统一入口）              |
| `com.hsmty.core.util.TreeUtils`                      | 树形结构转换                  |
| `com.hsmty.core.util.ConvertUtils`                   | 通用对象转换                  |
| `com.hsmty.core.util.SpringApplicationContextUtils`  | 获取 Spring Bean          |
| `com.hsmty.core.util.PanZhiHeaderUtils`              | 请求头解析                   |
| `com.hsmty.core.util.JsonUtils`                      | JSON 序列化/反序列化           |

代码中已在使用的配套工具（新增代码保持同一套）：

- `com.hsmty.core.util.BeanCopyUtils`：DTO/PO/VO 拷贝，替代手写 `setXxx`。
- `com.hsmty.core.util.PageUtils`：`getPage(dto)` / `getPageResult(page)`。
- `com.hsmty.core.util.Utils`：标量非空判断 `isNotNull(...)`。
- `com.hsmty.core.common.enums.CommonResponseEnum`：业务断言。
- `com.hsmty.core.common.entity.SelectIdsDTO` / `PageQuery`：批量操作与分页基类。
- `com.hsmty.core.feign.FeignConfig`：Feign 统一配置。
- `com.hsmty.db.EntityChangeListener` / `com.hsmty.db.id.SzIdGenerator`：审计字段填充与雪花 ID。

约定：

1. 集合/对象空值用 `ObjectUtil.isEmpty(...)`；标量用 `Utils.isNotNull(...)`，与模板代码保持一致。
2. 缓存操作不要直接注入 `RedisTemplate`，统一走 `RedisCache`。
3. README 中 `JsonUtils` 重复列了两次，属文档笔误，使用时按上述全限定名。
4. 公共工具若确需扩展，优先在 `hsmty-common-*` 中实现并升级版本，不在业务模块复制一份。

---

## 12. 构建、本地运行与数据库（README 约定）

### 12.1 Maven 仓库

- 项目根目录自带 `settings.xml`，Maven 仓库地址已配置好；CLI 使用 `mvn -s settings.xml ...`，IDEA 在 `Settings → Build Tools → Maven → User settings file` 指向该文件。

### 12.2 首次本地构建（重要）

子模块 POM 的 `<parent><relativePath/></parent>` 为空，父工程只能从仓库解析。首次构建按 README 执行：

1. 先注释掉根 `pom.xml` 的 `<modules>` 节点，执行一次：
   ```bash
   mvn -s settings.xml clean install
   ```
   把根工程安装到本地仓库。
2. 恢复 `<modules>` 节点后再次构建：
   ```bash
   mvn -s settings.xml clean package
   # 或只构建 core/start：
   mvn -s settings.xml -pl hsmty-module-xxx-core,hsmty-module-xxx-start -am clean package
   ```

### 12.3 本地运行

- 启动类：`com.hsmty.RunApplication`。
- 默认端口 `8080`，上下文 `/hs-api`。
- 接口文档：`http://localhost:8080/hs-api/swagger-ui.html`；OpenAPI：`/hs-api/v3/api-docs`。
- 本地执行数据库变更时显式开启 Liquibase：
  ```bash
  --spring.liquibase.enabled=true
  ```
- 切换数据库：默认 `mysql` profile；PostgreSQL 使用 `-Ppostgresql`。

### 12.4 数据库

- 统一使用 `sd_data_engineering`，已在 `application.yml` 配置；不要为单模块新建数据库。
- 表按 `{业务模块}_` 前缀隔离；公共表由 `hsmty-common-*` 维护。

---

## 13. 编码规范

1. UTF-8、换行 LF、缩进 4 空格（YAML/前端模板 2 空格），遵循 `.editorconfig` 与 `.gitattributes`；提交前确认 IDE 未改为 CRLF。
2. 包名全小写；类名大驼峰；方法/变量小驼峰；常量全大写下划线。
3. Lombok：`@Data`（PO/DTO/VO/Excel）、`@Slf4j`、`@RequiredArgsConstructor`；不要手写 getter/setter/构造器。
4. 类、接口、public 方法必须有 Javadoc，包含 `<p>` 描述与 `@author`、`@since`；字段用 `@Schema` 描述。
5. 空值判断统一 `Utils.isNotNull(...)` / `ObjectUtil.isEmpty(...)`。
6. 集合处理优先 `Stream`，避免多层嵌套；超过 3 层 `if` 提前 return 或抽方法。
7. 禁止吞异常；捕获后必须记录日志或转换为统一业务异常。
8. 业务代码禁止 `System.out.println`（仅启动 Banner 例外）；日志用 `@Slf4j`，错误日志带异常对象：`log.error(cause.getMessage(), cause)`。
9. 避免魔法值：状态、字典码、权限码、路径提取为常量或字典配置。
10. Java 21 特性可用，但不得牺牲可读性；新增公共工具先确认 `hsmty-common-*` 是否已有实现。
11. 注释、Javadoc、`@Schema` 描述必须与业务一致，禁止保留模板的“充电模块 / charging”等错误措辞。

---

## 14. 测试规范

1. 业务逻辑测试放 `core`；装配级/集成测试放 `start`；client 不写测试（`skipTests=true`）。
2. 当前模板只有 `start/src/test/resources/logback-test.xml`，**尚无测试类**；新增测试使用 JUnit 5 + AssertJ + `spring-boot-starter-test`（core/start 已引入）。
3. 默认构建跳过测试：`client/pom.xml` 设置 `skipTests=true`，`start/pom.xml` 的 surefire 也配置了 `skipTests=true`。新增测试后必须临时移除/调整该配置或通过独立 profile 执行，并确认用例实际运行（不要被“BUILD SUCCESS”误导）。
4. 集成测试使用 `@SpringBootTest(webEnvironment = NONE, properties = {...})`，通过 `properties` 注入最小配置，**不要依赖本地 `application.yml`**；涉及数据源/Redis 的用例使用测试专用配置或 mock。
5. 启动类与关键配置的断言（`@SpringBootApplication`、`@EnableAspectJAutoProxy`、`@EnableFeignClients` 存在）应保留，防止误删。
6. 新增接口至少覆盖：正常流程、参数校验失败、权限不足（如可测）、逻辑删除后的查询隔离。

---

## 15. Git 提交规范

1. 分支：`master` 为主干；功能 `feature/{业务}-{简述}`，缺陷 `fix/{业务}-{简述}`。
2. 提交信息：`{type}({scope}): {描述}`，`type` ∈ `feat|fix|refactor|docs|style|test|build|chore`，`scope` 用业务短名：
   ```
   feat(order): 新增订单分页查询
   fix(order): 修复逻辑删除后详情仍可查询
   ```
3. 一个提交只做一件事；变更数据库脚本、接口契约、配置项时必须在提交说明中标注。
4. 禁止提交 `target/`、`.idea/`、`logs/`、`data/`、`*.iml`、`**/.flattened-pom.xml`（已由 `.gitignore` 忽略）。
5. 合并前必须通过第 12.2 节的构建命令；涉及数据库变更时同时验证 Liquibase 重复执行幂等。

---

## 16. 新建业务模块落地清单

### 16.1 落地步骤

1. 复制本工程，按第 1.2 节替换 `xxx`、`Xxx`、`xxx_table`、模板文案、表前缀、字典类型。
2. 修改根 `pom.xml` 的 `artifactId`；三个子模块 `artifactId` 同步；版本沿用父工程管理的 `revision`。
3. 重命名 Java 包 `com.hsmty.xxx`（client/core），同步修改：
   - `XxxApiPrefixConfiguration` 的 `module` / `prefix` / `basePackages`；
   - `XxxMapperScanConfiguration` 的 `basePackages`；
   - `XxxMapper.xml` 的 `namespace` 与 `type`；
   - `@FeignClient` 的 `name` / `contextId`。
4. `RunApplication` 保持在 `com.hsmty` 包，确认扫描范围覆盖新包。
5. 修改 `application.yml`：
   - `springdoc.group-configs[0].group` 与 `packages-to-scan`；
   - `hsmty.api-prefix.modules.xxx`；
   - `{业务}.service.url`（与 context-path `/hs-api` 对齐）；
   - 数据源、Redis、Jasypt 密钥（禁止保留模板值）；
   - 端口/context-path 如需调整，全项目统一。
6. Liquibase：重命名 `db/changelog/{业务}/`、`module-xxx-changelog.xml`，同步主 changelog 的 `include`，补全 `001_xxx_init.xml` 建表脚本。
7. 修改 `XxxExcel` 的 `@DictFormat(dictType = ...)` 为实际字典类型；VO/Excel 展示字段按业务增删。
8. 按实际表结构重写 `XxxEntity` 字段，保证与建表脚本、`BaseResultMap`、`Base_Column_List` 一一对应。
9. 权限码三处一致：Controller `@PreAuthorize`、菜单 `permissions`、初始化脚本。
10. 检查依赖：core 新增 Web 依赖必须 `provided/optional`；client 不得出现 `spring-boot-starter-web`。
11. 按 README 完成首次构建（第 12.2 节），启动 `RunApplication`，验证：
    - 启动日志出现 `Register API prefix module=...`；
    - `/hs-api/{业务}` 接口可访问，`/hs-api/v3/api-docs` 分组正确；
    - Liquibase 变更按预期执行，重复启动幂等。
12. 删除模板残留资源与占位文件（示例 Excel、无关素材），避免带入生产包。

### 16.2 模板已知问题（落地必改）

| 位置                                                    | 问题                                                       | 处理                                             |
| ----------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------- |
| `XxxServiceImpl`                                      | 类上 `@RequiredArgsConstructor` 同时使用 `@Autowired` 注入 Feign | 改为 `private final XxxFeignClient xxxFeignClient;` |
| `XxxApiPrefixConfiguration`                           | 方法名 `chargingApiPrefixRegister`、Javadoc 为“充电模块”       | 改为业务命名                                          |
| `XxxMapperScanConfiguration`                          | Javadoc 为 `hsmty-module-charging`                        | 改为实际模块名                                        |
| `XxxEntity`                                           | 表名 `xxx_table` 不符合 `{模块}_{对象}`                          | 改为实际表名                                         |
| `XxxFeignClient`                                      | `Collection<?>`、摘要“查询行政区域详情”                         | 改为 `Collection<Long>` 与实际摘要                     |
| `application.yml`                                     | `xxx.service.url` 为 `.../api`，与 context-path `/hs-api` 不一致 | 按实际部署地址对齐                                      |
| `application.yml`                                     | `operations-sorter: alpha·` 含多余字符                         | 去掉 `·`                                         |
| `001_xxx_init.xml`                                    | 空文件                                                      | 补全建表 changeSet                                 |
| `README.md`                                           | `JsonUtils` 重复列出                                         | 修正文档                                           |

---

## 17. 速查表

| 场景                   | 应该放哪                                            |
| -------------------- | ----------------------------------------------- |
| 其它服务要调用的接口契约         | `client` → `feign` + `pojo/dto`、`pojo/vo`         |
| 本服务的 REST 接口         | `core` → `controller`                           |
| 业务逻辑、事务、远程编排         | `core` → `service.impl`                         |
| SQL / 数据访问           | `core` → `mapper`（复杂 SQL 才写 XML）                |
| 数据库实体 / Excel 模型      | `core` → `pojo.po` / `pojo.excel`               |
| 模块前缀、MapperScan      | `core` → `config`                               |
| 启动类、全局 Web/文档配置       | `start` → 根包 / `configuration`                   |
| 全局配置项                | `start` → `application.yml`                     |
| 建表、字典、菜单初始化          | `core` → `resources/db/changelog/{业务}/`         |
| 表名                   | 必须为 `{业务模块}_{对象}`，禁止无前缀业务表                       |
| 权限码                  | `{业务}:{动作}` 或 `{业务}:{资源}:{动作}`，三处一致            |
| 空值判断                 | `Utils.isNotNull(...)` / `ObjectUtil.isEmpty(...)` |
| 接口返回                 | `ApiResult` / `ApiPageResult`                   |
| 缓存                   | `com.hsmty.redis.RedisCache`                    |
| 集成测试                 | `start` → `src/test/java`                       |
