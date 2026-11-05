package com.wbdz.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

/**
 * 任务阈值调整入参。
 *
 * @param threshold 新阈值，范围 (0, 1]
 * @author wbdz
 * @since 2026-11-05
 */
@Schema(description = "任务阈值调整入参")
public record TaskThresholdDTO(
        @Schema(description = "新阈值，范围 (0, 1]", example = "0.8")
        @NotNull(message = "阈值不能为空")
        @DecimalMin(value = "0", inclusive = false, message = "阈值必须大于 0")
        @DecimalMax(value = "1", message = "阈值不能大于 1")
        BigDecimal threshold) {
}