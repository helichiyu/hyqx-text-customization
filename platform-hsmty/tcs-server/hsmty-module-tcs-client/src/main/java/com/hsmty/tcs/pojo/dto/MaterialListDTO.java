package com.hsmty.tcs.pojo.dto;

import com.hsmty.core.common.entity.PageQuery;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * <p>素材批次分页查询入参。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "素材批次分页查询入参")
public class MaterialListDTO extends PageQuery {

    @Schema(description = "产线代码：metadata/formula/layout/graphic", example = "metadata")
    private String line;

    @Schema(description = "批次名称关键字", example = "新闻素材")
    private String name;

    @Schema(description = "批次状态：uncheked/checked/released/upload_failed", example = "checked")
    private String status;
}
