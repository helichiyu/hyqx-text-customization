package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 算子产物文件。
 *
 * @param name 相对路径
 * @param size 文件大小，单位字节
 * @author wbdz
 * @since 2026-11-05
 */
@Schema(description = "算子产物文件")
public record ArtifactFileVO(
        @Schema(description = "相对路径") String name,
        @Schema(description = "文件大小，单位字节") Long size) {
}