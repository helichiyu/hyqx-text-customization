package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.math.BigDecimal;
import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 数据集明细行（records.jsonl 一行一条；复核 B 修正后以 revised 为准）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_dataset_item", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "数据集明细行")
public class DatasetItem implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "数据集内部主键")
    private Long datasetId;

    @Schema(description = "任务内部主键")
    private Long taskId;

    @Schema(description = "数据集行标识")
    private String itemKey;

    /** 算子行 JSON（B 修正后同步更新）。 */
    @Schema(description = "原始行 JSON")
    private String payload;

    /** 未进入复核/待复核/已确认A/已修正B/已剔除C。 */
    @Schema(description = "复核状态")
    private String reviewStatus;

    /** -/未修正/已修正/已剔除。 */
    @Schema(description = "修正状态")
    private String revisionStatus;

    /** 行级最低置信度（展示用）。 */
    @Schema(description = "置信度")
    private BigDecimal confidence;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
