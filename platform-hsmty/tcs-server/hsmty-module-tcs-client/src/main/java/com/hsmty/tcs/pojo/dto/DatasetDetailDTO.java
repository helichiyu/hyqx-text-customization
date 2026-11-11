package com.hsmty.tcs.pojo.dto;

import com.hsmty.core.common.entity.PageQuery;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * <p>数据集详情查询入参：明细分页与复核状态过滤。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "数据集详情查询入参")
public class DatasetDetailDTO extends PageQuery {

    @Schema(description = "明细复核状态过滤", example = "待复核")
    private String reviewStatus;
}
