package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 当前登录用户。
 *
 * @param id 用户内部主键
 * @param username 登录名
 * @param nickname 昵称
 * @author wbdz
 * @since 2026-11-05
 */
@Schema(description = "当前登录用户")
public record CurrentUserVO(
        @Schema(description = "用户内部主键") Long id,
        @Schema(description = "登录名") String username,
        @Schema(description = "昵称") String nickname) {
}