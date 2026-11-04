package com.wbdz.entity;

import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 生产任务。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_task", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class TaskMain {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    /** TASK + yyMMdd + 随机码。 */
    private String bizNo;

    private String name;

    private String line;

    /** draft/pending/processing/waitreview/quality/collected/reject。 */
    private String status;

    /** high/mid/low。 */
    private String priority;

    /** 图文融合任务大类：几何/统计/表格/示意。 */
    private String imageClass;

    private Long batchId;

    /** 创建时锁定的参数版本号（如 v2.0）。 */
    private String paramVersion;

    /** 参数快照 JSON。 */
    private String paramSnapshot;

    /** 任务级置信度阈值（默认 0.80，数据集明细可调）。 */
    private BigDecimal threshold;

    /** 当前执行环节号 1-3（0=未开始）。 */
    private Integer currentStage;

    private String createBy;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    @Column(isLogicDelete = true)
    private String delFlag;
}
