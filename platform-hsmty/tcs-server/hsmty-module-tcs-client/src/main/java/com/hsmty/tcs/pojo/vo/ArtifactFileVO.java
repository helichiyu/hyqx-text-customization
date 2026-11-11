package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * <p>算子产物文件。
 *
 * @param name 相对路径
 * @param size 文件大小，单位字节
 * @author helichiyu
 * @since 2.0.1
 */
@Schema(description = "算子产物文件")
public record ArtifactFileVO(
        @Schema(description = "相对路径") String name,
        @Schema(description = "文件大小，单位字节") Long size) {
}
