package com.hsmty.tcs.pojo.dto;

import com.hsmty.core.common.entity.PageQuery;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * <p>复核单分页查询入参。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "复核单分页查询入参")
public class ReviewListDTO extends PageQuery {

    @Schema(description = "复核单状态：pending/doing/done/void", example = "pending")
    private String status;

    @Schema(description = "产线代码", example = "metadata")
    private String line;

    @Schema(description = "来源任务内部主键")
    private Long taskId;
}
