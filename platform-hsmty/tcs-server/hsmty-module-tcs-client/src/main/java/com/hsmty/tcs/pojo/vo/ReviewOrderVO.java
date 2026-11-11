package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * <p>复核单基础信息。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Schema(description = "复核单基础信息")
public class ReviewOrderVO {

    @Schema(description = "复核单内部主键")
    private Long id;

    @Schema(description = "复核单业务编号")
    private String bizNo;

    @Schema(description = "来源任务内部主键")
    private Long taskId;

    @Schema(description = "来源任务业务编号")
    private String taskBizNo;

    @Schema(description = "产线代码")
    private String line;

    @Schema(description = "产线中文名")
    private String lineName;

    @Schema(description = "来源环节名称")
    private String stageName;

    @Schema(description = "触发原因分类码")
    private String triggerCode;

    @Schema(description = "触发原因描述")
    private String triggerDesc;

    @Schema(description = "复核条目数")
    private Integer itemCount;

    @Schema(description = "复核单状态")
    private String status;

    @Schema(description = "复核单状态中文名")
    private String statusName;

    @Schema(description = "创建时间")
    private String createTime;

    @Schema(description = "闭环操作人")
    private String closeBy;

    @Schema(description = "闭环时间")
    private String closeTime;
}
