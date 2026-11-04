package com.wbdz.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 登录入参。
 *
 * @param username 登录名
 * @param password 密码
 * @author wbdz
 * @since 2026-11-03
 */
public record LoginDTO(
        @NotBlank(message = "登录名不能为空") String username,
        @NotBlank(message = "密码不能为空") String password) {
}
