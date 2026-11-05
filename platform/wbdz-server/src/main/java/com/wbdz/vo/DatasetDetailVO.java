package com.wbdz.vo;

import com.wbdz.common.PageResult;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 数据集详情聚合响应。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "数据集详情聚合响应")
public class DatasetDetailVO extends DatasetVO {
    @Schema(description = "来源任务摘要")
    private TaskBrief task;
    @Schema(description = "主执行记录内部主键")
    private Long runId;
    @Schema(description = "图片执行记录内部主键")
    private Long imageRunId;
    @Schema(description = "数据集明细分页")
    private PageResult<Item> items;
    @Schema(description = "交付记录")
    private List<Delivery> deliveries;
    @Schema(description = "回滚记录")
    private List<Rollback> rollbacks;

    @Data
    @Schema(description = "数据集来源任务摘要")
    public static class TaskBrief {
        @Schema(description = "任务内部主键")
        private Long id;
        @Schema(description = "任务业务编号")
        private String bizNo;
        @Schema(description = "任务名称")
        private String name;
        @Schema(description = "产线代码")
        private String line;
        @Schema(description = "置信度阈值")
        private BigDecimal threshold;
    }

    @Data
    @Schema(description = "数据集明细行")
    public static class Item {
        @Schema(description = "明细内部主键")
        private Long id;
        @Schema(description = "数据集行标识")
        private String itemKey;
        @Schema(description = "算子原始行")
        private Map<String, Object> payload;
        @Schema(description = "复核状态")
        private String reviewStatus;
        @Schema(description = "修正状态")
        private String revisionStatus;
        @Schema(description = "置信度")
        private BigDecimal confidence;
    }

    @Data
    @Schema(description = "数据集交付记录")
    public static class Delivery {
        @Schema(description = "交付记录业务编号")
        private String bizNo;
        @Schema(description = "交付类型")
        private String type;
        @Schema(description = "文件名")
        private String filename;
        @Schema(description = "操作人")
        private String operator;
        @Schema(description = "交付时间")
        private String time;
    }

    @Data
    @Schema(description = "数据集回滚记录")
    public static class Rollback {
        @Schema(description = "回滚记录业务编号")
        private String bizNo;
        @Schema(description = "回滚目标")
        private String target;
        @Schema(description = "回滚原因")
        private String reason;
        @Schema(description = "操作人")
        private String operator;
        @Schema(description = "操作时间")
        private String time;
    }
}