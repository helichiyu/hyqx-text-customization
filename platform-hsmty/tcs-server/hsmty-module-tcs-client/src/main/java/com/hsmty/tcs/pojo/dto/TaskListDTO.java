package com.hsmty.tcs.pojo.dto;

import com.hsmty.core.common.entity.PageQuery;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * <p>生产任务分页查询入参。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "生产任务分页查询入参")
public class TaskListDTO extends PageQuery {

    @Schema(description = "产线代码：metadata/formula/layout/graphic", example = "metadata")
    private String line;

    @Schema(description = "任务状态", example = "draft")
    private String status;

    @Schema(description = "任务名称关键字", example = "新闻")
    private String name;

    @Schema(description = "优先级：high/mid/low", example = "mid")
    private String priority;
}
