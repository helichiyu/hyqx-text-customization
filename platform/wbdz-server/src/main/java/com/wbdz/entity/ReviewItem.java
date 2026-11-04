package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 复核条目（一文档/一页/一公式/一图一条）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_review_item", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class ReviewItem {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    private Long orderId;

    private Long taskId;

    /** 算子数据集行主键（docId/pageId/公式实例 id）。 */
    private String itemKey;

    /** 触发码（low_confidence/conflict/...）。 */
    private String code;

    /** 触发说明（中文）。 */
    private String reason;

    /** 算子原始行 JSON（含全部字段与置信度）。 */
    private String payload;

    /** 结论：null/A/B/C。 */
    private String conclusion;

    /** B 修正后的行 JSON。 */
    private String revisedPayload;

    /** 修正字段改前值 JSON（{field: oldValue}）。 */
    private String beforeValue;

    /** 修正字段改后值 JSON。 */
    private String afterValue;

    private String operator;

    private LocalDateTime concludeTime;

    private LocalDateTime createTime;
}
