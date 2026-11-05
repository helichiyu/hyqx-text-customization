package com.wbdz.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

/**
 * 参数草稿保存 / 发布入参。
 *
 * @param line    产线代码或 common
 * @param content 参数组 JSON 字符串：[{name,value,desc}]（发布时可不传，取草稿）
 * @author wbdz
 * @since 2026-11-03
 */
@Schema(description = "参数草稿保存或发布入参")
public record ParamSaveDTO(
        @Schema(description = "产线代码或 common", example = "metadata")
        @NotBlank(message = "产线不能为空")
        String line,
        @Schema(description = "参数组 JSON 字符串")
        String content) {
}