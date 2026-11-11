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
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * <p>数据集行（算子原始产出，复核后回写 reviewStatus/revisionStatus）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_dataset_item", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "数据集行")
public class DatasetItemEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "数据集内部主键")
    private Long datasetId;

    @Schema(description = "任务内部主键")
    private Long taskId;

    @Schema(description = "行标识")
    private String itemKey;

    @Schema(description = "算子原始行 JSON")
    private String payload;

    @Schema(description = "复核状态：PASS/FAIL/ADJUSTED/空")
    private String reviewStatus;

    @Schema(description = "修正状态：A/B/C/空")
    private String revisionStatus;

    @Schema(description = "置信度")
    private BigDecimal confidence;

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
