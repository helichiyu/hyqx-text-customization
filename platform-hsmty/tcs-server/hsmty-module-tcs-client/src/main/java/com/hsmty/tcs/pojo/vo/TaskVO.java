package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.math.BigDecimal;

/**
 * <p>任务基础信息。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Schema(description = "任务基础信息")
public class TaskVO {

    @Schema(description = "内部主键", example = "2074457061897732097")
    private Long id;

    @Schema(description = "任务业务编号", example = "TASK261026A3F9KX")
    private String bizNo;

    @Schema(description = "任务名称")
    private String name;

    @Schema(description = "产线代码", example = "metadata")
    private String line;

    @Schema(description = "产线中文名", example = "文本元信息")
    private String lineName;

    @Schema(description = "任务状态", example = "draft")
    private String status;

    @Schema(description = "任务状态中文名", example = "草稿")
    private String statusName;

    @Schema(description = "优先级：high/mid/low", example = "mid")
    private String priority;

    @Schema(description = "图文融合任务大类", example = "统计")
    private String imageClass;

    @Schema(description = "素材批次内部主键")
    private Long batchId;

    @Schema(description = "参数版本号", example = "v1.0")
    private String paramVersion;

    @Schema(description = "任务级置信度阈值", example = "0.8")
    private BigDecimal threshold;

    @Schema(description = "当前执行环节号，0 表示未开始", example = "1")
    private Integer currentStage;

    @Schema(description = "创建人")
    private String createBy;

    @Schema(description = "创建时间")
    private String createTime;
}
