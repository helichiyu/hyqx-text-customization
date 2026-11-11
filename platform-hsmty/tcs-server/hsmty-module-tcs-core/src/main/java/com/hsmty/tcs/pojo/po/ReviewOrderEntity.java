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
 * <p>条件复核单。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_review_order", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "复核单")
public class ReviewOrderEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "业务编号：CR + yyMMdd + 随机码")
    private String bizNo;

    @Schema(description = "任务内部主键")
    private Long taskId;

    @Schema(description = "产线代码")
    private String line;

    @Schema(description = "触发环节名")
    private String stageName;

    @Schema(description = "触发原因分类码（逗号分隔多码）")
    private String triggerCode;

    @Schema(description = "触发原因描述")
    private String triggerDesc;

    @Schema(description = "条目数")
    private Integer itemCount;

    @Schema(description = "状态：pending/doing/done/void")
    private String status;

    @Schema(description = "创建人展示名")
    private String createBy;

    @Schema(description = "闭环操作人")
    private String closeBy;

    @Schema(description = "闭环时间")
    private LocalDateTime closeTime;

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
