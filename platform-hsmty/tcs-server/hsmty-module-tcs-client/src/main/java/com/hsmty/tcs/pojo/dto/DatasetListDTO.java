package com.hsmty.tcs.pojo.dto;

import com.hsmty.core.common.entity.PageQuery;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * <p>数据集分页查询入参。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "数据集分页查询入参")
public class DatasetListDTO extends PageQuery {

    @Schema(description = "产线代码", example = "metadata")
    private String line;

    @Schema(description = "数据集状态：candidate/published/rolledback", example = "candidate")
    private String status;

    @Schema(description = "数据集业务编号关键字", example = "DS")
    private String keyword;
}
