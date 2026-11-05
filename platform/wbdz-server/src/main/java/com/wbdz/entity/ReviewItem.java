package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 复核条目（一文档/一页/一公式/一图一条）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_review_item", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "复核条目")
public class ReviewItem implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "复核单内部主键")
    private Long orderId;

    @Schema(description = "任务内部主键")
    private Long taskId;

    /** 算子数据集行主键（docId/pageId/公式实例 id）。 */
    @Schema(description = "数据集行标识")
    private String itemKey;

    /** 触发码（low_confidence/conflict/...）。 */
    @Schema(description = "原因分类码")
    private String code;

    /** 触发说明（中文）。 */
    @Schema(description = "原因")
    private String reason;

    /** 算子原始行 JSON（含全部字段与置信度）。 */
    @Schema(description = "原始行 JSON")
    private String payload;

    /** 结论：null/A/B/C。 */
    @Schema(description = "复核结论")
    private String conclusion;

    /** B 修正后的行 JSON。 */
    @Schema(description = "修正后行 JSON")
    private String revisedPayload;

    /** 修正字段改前值 JSON（{field: oldValue}）。 */
    @Schema(description = "修正前字段 JSON")
    private String beforeValue;

    /** 修正字段改后值 JSON。 */
    @Schema(description = "修正后字段 JSON")
    private String afterValue;

    @Schema(description = "操作人")
    private String operator;

    @Schema(description = "结论时间")
    private LocalDateTime concludeTime;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
