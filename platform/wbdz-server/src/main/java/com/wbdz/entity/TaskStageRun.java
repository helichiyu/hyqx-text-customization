package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 任务环节执行记录（每次 predict 一条；重跑 attempt+1 产生新记录）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_task_stage_run", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "环节执行记录")
public class TaskStageRun implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "任务内部主键")
    private Long taskId;

    /** 环节号 1-3。 */
    @Schema(description = "环节号")
    private Integer stageNo;

    @Schema(description = "环节名称")
    private String stageName;

    /** 承接该环节的算子目录名。 */
    @Schema(description = "算子标识")
    private String operatorTag;

    /** running/done/error。 */
    @Schema(description = "状态")
    private String status;

    /** 算子返回 summary JSON。 */
    @Schema(description = "汇总 JSON")
    private String summary;

    /** skipped JSON。 */
    @Schema(description = "跳过条目 JSON")
    private String skipped;

    /** failed JSON。 */
    @Schema(description = "失败条目 JSON")
    private String failed;

    /** 算子输出目录（inputFile 透传用）。 */
    @Schema(description = "输出路径")
    private String outputPath;

    /** 第几次尝试（1 起，重跑递增）。 */
    @Schema(description = "尝试次数")
    private Integer attempt;

    @Schema(description = "开始时间")
    private LocalDateTime startTime;

    @Schema(description = "结束时间")
    private LocalDateTime endTime;
}
