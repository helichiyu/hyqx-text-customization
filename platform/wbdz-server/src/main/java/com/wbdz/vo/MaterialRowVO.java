package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 素材批次列表行。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "素材批次列表行")
public class MaterialRowVO extends MaterialVO {
    @Schema(description = "关联任务数量")
    private Integer linkedTaskCount;
    @Schema(description = "是否已被非草稿任务关联")
    private Boolean linked;
}