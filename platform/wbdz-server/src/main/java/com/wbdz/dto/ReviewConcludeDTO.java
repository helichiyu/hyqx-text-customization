package com.wbdz.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import java.util.Map;

/**
 * 复核条目结论入参。
 *
 * @param conclusion     A 确认 / B 修正 / C 剔除
 * @param revisedPayload B 时必填：修正后的完整行（仅需提交要改的字段）
 * @author wbdz
 * @since 2026-11-03
 */
@Schema(description = "复核条目结论入参")
public record ReviewConcludeDTO(
        @Schema(description = "复核结论：A 确认 / B 修正 / C 剔除", example = "A")
        @NotBlank(message = "结论不能为空")
        @Pattern(regexp = "^[ABC]$", message = "结论只能是 A、B 或 C")
        String conclusion,
        @Schema(description = "B 类修正后的数据行")
        Map<String, Object> revisedPayload) {
}