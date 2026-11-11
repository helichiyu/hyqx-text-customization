package com.hsmty.tcs.pojo.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * <p>数据集回滚入参。
 *
 * @param reason 回滚原因，必须留痕
 * @author helichiyu
 * @since 2.0.1
 */
@Schema(description = "数据集回滚入参")
public record DatasetRollbackDTO(
        @Schema(description = "回滚原因", example = "复核发现字段缺失")
        @NotBlank(message = "回滚原因不能为空")
        @Size(max = 500, message = "回滚原因不能超过 500 个字符")
        String reason) {
}
