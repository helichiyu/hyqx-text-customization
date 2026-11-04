package com.wbdz.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

/**
 * 草稿任务修改入参。
 *
 * @param name         任务名称
 * @param batchId      素材批次
 * @param priority     优先级
 * @param imageClass   图文融合任务大类
 * @param paramVersion 参数版本号
 * @param threshold    任务级置信度阈值
 * @author wbdz
 * @since 2026-11-04
 */
public record TaskUpdateDTO(
        @NotBlank(message = "任务名称不能为空") String name,
        @NotNull(message = "素材批次不能为空") Long batchId,
        String priority,
        String imageClass,
        String paramVersion,
        @DecimalMin(value = "0", inclusive = false, message = "阈值必须大于 0")
        @DecimalMax(value = "1", message = "阈值不能大于 1")
        BigDecimal threshold) {
}
