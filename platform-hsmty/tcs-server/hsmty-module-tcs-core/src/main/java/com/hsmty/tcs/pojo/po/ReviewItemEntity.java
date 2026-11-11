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
 * <p>复核条目（一文档/一页/一公式/一图一条）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_review_item", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "复核条目")
public class ReviewItemEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "复核单内部主键")
    private Long orderId;

    @Schema(description = "任务内部主键")
    private Long taskId;

    @Schema(description = "数据集行标识")
    private String itemKey;

    @Schema(description = "触发码")
    private String code;

    @Schema(description = "触发说明")
    private String reason;

    @Schema(description = "算子原始行 JSON")
    private String payload;

    @Schema(description = "结论：A/B/C，空为未处理")
    private String conclusion;

    @Schema(description = "B 修正后的行 JSON")
    private String revisedPayload;

    @Schema(description = "修正字段改前值 JSON")
    private String beforeValue;

    @Schema(description = "修正字段改后值 JSON")
    private String afterValue;

    @Schema(description = "结论操作人")
    private String operator;

    @Schema(description = "结论时间")
    private LocalDateTime concludeTime;

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
