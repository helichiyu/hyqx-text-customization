package com.wbdz.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.Map;

/**
 * 复核条目结论入参。
 *
 * @param conclusion     A 确认 / B 修正 / C 剔除
 * @param revisedPayload B 时必填：修正后的完整行（仅需提交要改的字段）
 * @author wbdz
 * @since 2026-11-03
 */
public record ReviewConcludeDTO(
        @NotBlank(message = "结论不能为空") String conclusion,
        Map<String, Object> revisedPayload) {
}
