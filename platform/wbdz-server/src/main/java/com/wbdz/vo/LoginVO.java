package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 登录结果。
 *
 * @param token JWT 令牌
 * @author wbdz
 * @since 2026-11-05
 */
@Schema(description = "登录结果")
public record LoginVO(@Schema(description = "JWT 令牌") String token) {
}