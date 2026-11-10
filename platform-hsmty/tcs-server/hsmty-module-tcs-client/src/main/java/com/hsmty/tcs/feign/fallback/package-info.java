/**
 * <p>Feign 熔断降级工厂包。
 *
 * <p>每个 Feign 接口对应一个 {@code FallbackFactory}，记录 {@code cause} 后返回
 * {@code feign.impl} 中的降级实现。
 *
 * @author helichiyu
 * @since 2.0.1
 */
package com.hsmty.tcs.feign.fallback;
