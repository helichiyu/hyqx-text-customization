package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 任务环节执行记录（每次 predict 一条；重跑 attempt+1 产生新记录）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_task_stage_run", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class TaskStageRun {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    private Long taskId;

    /** 环节号 1-3。 */
    private Integer stageNo;

    private String stageName;

    /** 承接该环节的算子目录名。 */
    private String operatorTag;

    /** running/done/error。 */
    private String status;

    /** 算子返回 summary JSON。 */
    private String summary;

    /** skipped JSON。 */
    private String skipped;

    /** failed JSON。 */
    private String failed;

    /** 算子输出目录（inputFile 透传用）。 */
    private String outputPath;

    /** 第几次尝试（1 起，重跑递增）。 */
    private Integer attempt;

    private LocalDateTime startTime;

    private LocalDateTime endTime;
}
