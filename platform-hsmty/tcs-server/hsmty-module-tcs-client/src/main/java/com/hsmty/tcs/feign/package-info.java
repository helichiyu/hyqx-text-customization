/**
 * <p>对外 Feign 契约包。
 *
 * <p>只放其它服务调用本服务所需的 Feign 接口：{@code name} 使用逻辑服务名
 * {@code hsmty-tcs-server}，{@code contextId} 全局唯一，地址来自
 * {@code tcs.service.url} 配置项。
 *
 * <p>业务迁移时在此补充接口，并同步在 {@code feign.fallback} 与 {@code feign.impl}
 * 提供降级实现；禁止在本包依赖 core/start。
 *
 * @author helichiyu
 * @since 2.0.1
 */
package com.hsmty.tcs.feign;
