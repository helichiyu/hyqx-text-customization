package com.wbdz.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

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
@Schema(description = "任务创建入参")
public record TaskCreateDTO(
        @Schema(description = "任务名称", example = "新闻元信息抽取")
        @NotBlank(message = "任务名称不能为空")
        @Size(max = 100, message = "任务名称不能超过 100 个字符")
        String name,
        @Schema(description = "产线代码", example = "metadata")
        @NotBlank(message = "产线不能为空")
        String line,
        @Schema(description = "素材批次内部主键")
        @NotNull(message = "素材批次不能为空")
        Long batchId,
        @Schema(description = "优先级：high/mid/low", example = "mid")
        @Pattern(regexp = "^(high|mid|low)$", message = "优先级取值：high/mid/low")
        String priority,
        @Schema(description = "图文融合任务大类", example = "统计")
        String imageClass,
        @Schema(description = "参数版本号；为空取最新版本", example = "v1.0")
        String paramVersion,
        @Schema(description = "任务级置信度阈值", example = "0.8")
        @DecimalMin(value = "0", inclusive = false, message = "阈值必须大于 0")
        @DecimalMax(value = "1", message = "阈值不能大于 1")
        BigDecimal threshold) {
}