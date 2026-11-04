package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 条件复核单。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_review_order", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class ReviewOrder {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    /** CR + yyMMdd + 随机码。 */
    private String bizNo;

    private Long taskId;

    private String line;

    /** 触发环节名。 */
    private String stageName;

    /** 触发原因分类码（算子 code，逗号分隔多码）。 */
    private String triggerCode;

    /** 触发原因描述（中文，可直接展示）。 */
    private String triggerDesc;

    private Integer itemCount;

    /** pending/doing/done/void。 */
    private String status;

    private String createBy;

    private LocalDateTime createTime;

    private String closeBy;

    private LocalDateTime closeTime;
}
