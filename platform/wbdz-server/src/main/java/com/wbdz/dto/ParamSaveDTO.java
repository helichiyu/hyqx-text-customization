package com.wbdz.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 参数草稿保存 / 发布入参。
 *
 * @param line    产线代码或 common
 * @param content 参数组 JSON 字符串：[{name,value,desc}]（发布时可不传，取草稿）
 * @author wbdz
 * @since 2026-11-03
 */
public record ParamSaveDTO(
        @NotBlank(message = "产线不能为空") String line,
        String content) {
}
