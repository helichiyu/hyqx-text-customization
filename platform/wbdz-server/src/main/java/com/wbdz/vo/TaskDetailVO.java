package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.util.List;
import java.util.Map;

/**
 * 任务详情聚合响应。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "任务详情聚合响应")
public class TaskDetailVO extends TaskVO {

    @Schema(description = "三个执行环节名称")
    private List<String> stageNames;

    @Schema(description = "创建任务时锁定的参数快照")
    private List<Map<String, Object>> paramSnapshot;

    @Schema(description = "任务是否正在异步执行")
    private Boolean running;

    @Schema(description = "素材批次摘要")
    private Batch batch;

    @Schema(description = "环节执行记录")
    private List<StageRun> stageRuns;

    @Schema(description = "任务关联数据集")
    private List<DatasetBrief> datasets;

    @Schema(description = "任务关联复核单")
    private List<ReviewOrderBrief> reviewOrders;

    @Data
    @Schema(description = "任务素材批次摘要")
    public static class Batch {
        @Schema(description = "素材批次内部主键")
        private Long id;
        @Schema(description = "素材批次业务编号")
        private String bizNo;
        @Schema(description = "素材批次名称")
        private String name;
        @Schema(description = "有效素材条数")
        private Integer fileCount;
    }

    @Data
    @Schema(description = "环节执行记录")
    public static class StageRun {
        @Schema(description = "环节执行记录内部主键")
        private Long id;
        @Schema(description = "环节号")
        private Integer stageNo;
        @Schema(description = "环节名称")
        private String stageName;
        @Schema(description = "算子标识")
        private String operatorTag;
        @Schema(description = "执行状态")
        private String status;
        @Schema(description = "尝试次数")
        private Integer attempt;
        @Schema(description = "算子汇总结果")
        private Map<String, Object> summary;
        @Schema(description = "跳过条目")
        private List<Map<String, Object>> skipped;
        @Schema(description = "失败条目")
        private List<Map<String, Object>> failed;
        @Schema(description = "开始时间")
        private String startTime;
        @Schema(description = "结束时间")
        private String endTime;
        @Schema(description = "样本级实时进度")
        private Map<String, Object> progress;
    }

    @Data
    @Schema(description = "任务关联数据集摘要")
    public static class DatasetBrief {
        @Schema(description = "数据集内部主键")
        private Long id;
        @Schema(description = "数据集业务编号")
        private String bizNo;
        @Schema(description = "语义版本号")
        private String semVer;
        @Schema(description = "数据集状态")
        private String status;
        @Schema(description = "最终条数")
        private Integer itemCount;
        @Schema(description = "剔除条数")
        private Integer skipCount;
        @Schema(description = "创建时间")
        private String createTime;
    }

    @Data
    @Schema(description = "任务关联复核单摘要")
    public static class ReviewOrderBrief {
        @Schema(description = "复核单内部主键")
        private Long id;
        @Schema(description = "复核单业务编号")
        private String bizNo;
        @Schema(description = "复核单状态")
        private String status;
        @Schema(description = "来源环节名称")
        private String stageName;
        @Schema(description = "复核条目数")
        private Integer itemCount;
        @Schema(description = "触发原因描述")
        private String triggerDesc;
    }
}