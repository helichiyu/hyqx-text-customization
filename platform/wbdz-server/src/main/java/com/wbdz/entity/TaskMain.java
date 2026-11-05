package com.wbdz.entity;

import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.math.BigDecimal;
import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 生产任务。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_task", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "生产任务")
public class TaskMain implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    /** TASK + yyMMdd + 随机码。 */
    @Schema(description = "业务编号")
    private String bizNo;

    @Schema(description = "名称")
    private String name;

    @Schema(description = "产线代码")
    private String line;

    /** draft/pending/processing/waitreview/quality/collected/reject。 */
    @Schema(description = "状态")
    private String status;

    /** high/mid/low。 */
    @Schema(description = "优先级")
    private String priority;

    /** 图文融合任务大类：几何/统计/表格/示意。 */
    @Schema(description = "图文融合大类")
    private String imageClass;

    @Schema(description = "素材批次内部主键")
    private Long batchId;

    /** 创建时锁定的参数版本号（如 v2.0）。 */
    @Schema(description = "参数版本号")
    private String paramVersion;

    /** 参数快照 JSON。 */
    @Schema(description = "参数快照 JSON")
    private String paramSnapshot;

    /** 任务级置信度阈值（默认 0.80，数据集明细可调）。 */
    @Schema(description = "置信度阈值")
    private BigDecimal threshold;

    /** 当前执行环节号 1-3（0=未开始）。 */
    @Schema(description = "当前环节号")
    private Integer currentStage;

    @Schema(description = "创建人")
    private String createBy;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    @Schema(description = "更新时间")
    private LocalDateTime updateTime;

    @Column(isLogicDelete = true)
    @Schema(description = "逻辑删除标记")
    private String delFlag;
}
