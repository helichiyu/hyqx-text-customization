package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * <p>素材批次列表行。
 *
 * @author helichiyu
 * @since 2.0.1
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
