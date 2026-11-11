package com.hsmty.tcs.pojo.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Size;

/**
 * <p>素材批次基本信息编辑入参（两项均可选，至少传一项）。
 *
 * @param name 新批次名称
 * @param line 新产线代码
 * @author helichiyu
 * @since 2.0.1
 */
@Schema(description = "素材批次基本信息编辑入参")
public record MaterialEditDTO(
        @Schema(description = "新批次名称", example = "新闻素材 001")
        @Size(max = 100, message = "批次名称不能超过 100 个字符")
        String name,
        @Schema(description = "新产线代码", example = "metadata")
        String line) {

    /**
     * <p>至少提交一个非空修改项。
     *
     * @return 是否至少有一项修改
     */
    @AssertTrue(message = "批次名称和产线至少修改一项")
    @Schema(description = "是否至少修改一项", hidden = true)
    public boolean isAnyFieldPresent() {
        return (name != null && !name.isBlank()) || (line != null && !line.isBlank());
    }
}
