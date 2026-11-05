package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 条件复核单。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_review_order", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "复核单")
public class ReviewOrder implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    /** CR + yyMMdd + 随机码。 */
    @Schema(description = "业务编号")
    private String bizNo;

    @Schema(description = "任务内部主键")
    private Long taskId;

    @Schema(description = "产线代码")
    private String line;

    /** 触发环节名。 */
    @Schema(description = "环节名称")
    private String stageName;

    /** 触发原因分类码（算子 code，逗号分隔多码）。 */
    @Schema(description = "触发原因码")
    private String triggerCode;

    /** 触发原因描述（中文，可直接展示）。 */
    @Schema(description = "触发原因描述")
    private String triggerDesc;

    @Schema(description = "条目数")
    private Integer itemCount;

    /** pending/doing/done/void。 */
    @Schema(description = "状态")
    private String status;

    @Schema(description = "创建人")
    private String createBy;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    @Schema(description = "闭环操作人")
    private String closeBy;

    @Schema(description = "闭环时间")
    private LocalDateTime closeTime;
}
