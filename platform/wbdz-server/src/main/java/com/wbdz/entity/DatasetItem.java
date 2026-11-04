package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 数据集明细行（records.jsonl 一行一条；复核 B 修正后以 revised 为准）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_dataset_item", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class DatasetItem {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    private Long datasetId;

    private Long taskId;

    private String itemKey;

    /** 算子行 JSON（B 修正后同步更新）。 */
    private String payload;

    /** 未进入复核/待复核/已确认A/已修正B/已剔除C。 */
    private String reviewStatus;

    /** -/未修正/已修正/已剔除。 */
    private String revisionStatus;

    /** 行级最低置信度（展示用）。 */
    private BigDecimal confidence;

    private LocalDateTime createTime;
}
