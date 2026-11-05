package com.wbdz.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

/**
 * 登录入参。
 *
 * @param username 登录名
 * @param password 密码
 * @author wbdz
 * @since 2026-11-03
 */
@Schema(description = "登录入参")
public record LoginDTO(
        @Schema(description = "登录名", example = "admin")
        @NotBlank(message = "登录名不能为空")
        String username,
        @Schema(description = "密码", example = "wbdz123")
        @NotBlank(message = "密码不能为空")
        String password) {
}