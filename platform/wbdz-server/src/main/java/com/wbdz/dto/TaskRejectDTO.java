package com.wbdz.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

/**
 * 任务驳回重跑入参。
 *
 * @param fromStage 起始环节，1-3；为空时默认从第 1 环节重跑
 * @author wbdz
 * @since 2026-11-05
 */
@Schema(description = "任务驳回重跑入参")
public record TaskRejectDTO(
        @Schema(description = "起始环节，1-3", example = "1")
        @Min(value = 1, message = "起始环节不能小于 1")
        @Max(value = 3, message = "起始环节不能大于 3")
        Integer fromStage) {
}