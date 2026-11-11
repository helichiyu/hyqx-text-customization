package com.hsmty.tcs.pojo.po;

import com.hsmty.db.EntityChangeListener;
import com.hsmty.db.id.SzIdGenerator;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serial;
import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * <p>任务环节执行记录（每次 predict 一条；重跑产生新记录）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_task_stage_run", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "环节执行记录")
public class TaskStageRunEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "任务内部主键")
    private Long taskId;

    @Schema(description = "环节号 1-3")
    private Integer stageNo;

    @Schema(description = "环节名称")
    private String stageName;

    @Schema(description = "承接该环节的算子标识")
    private String operatorTag;

    @Schema(description = "状态：running/done/error")
    private String status;

    @Schema(description = "算子返回 summary JSON")
    private String summary;

    @Schema(description = "跳过条目 JSON")
    private String skipped;

    @Schema(description = "失败条目 JSON")
    private String failed;

    @Schema(description = "算子输出路径")
    private String outputPath;

    @Schema(description = "第几次尝试（1 起，重跑递增）")
    private Integer attempt;

    @Schema(description = "开始时间")
    private LocalDateTime startTime;

    @Schema(description = "结束时间")
    private LocalDateTime endTime;

    @Schema(description = "创建人 ID")
    private String createId;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    @Schema(description = "更新人 ID")
    private String updateId;

    @Schema(description = "更新时间")
    private LocalDateTime updateTime;

    @Column(isLogicDelete = true)
    @Schema(description = "逻辑删除标记")
    private String delFlag;
}
