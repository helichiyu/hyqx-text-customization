package com.wbdz.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

/**
 * 任务创建入参。
 *
 * @param name         任务名称
 * @param line         产线代码
 * @param batchId      素材批次（须已移交）
 * @param priority     high/mid/low（默认 mid）
 * @param imageClass   图文融合任务大类（图文线必填：几何/统计/表格/示意）
 * @param paramVersion 参数版本号（默认取该产线最新）
 * @param threshold    任务级置信度阈值（默认 0.80）
 * @author wbdz
 * @since 2026-11-03
 */
public record TaskCreateDTO(
        @NotBlank(message = "任务名称不能为空") String name,
        @NotBlank(message = "产线不能为空") String line,
        @NotNull(message = "素材批次不能为空") Long batchId,
        String priority,
        String imageClass,
        String paramVersion,
        BigDecimal threshold) {
}
