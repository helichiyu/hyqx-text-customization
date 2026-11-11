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
 * <p>生产任务。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_task", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "生产任务")
public class TaskMainEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "业务编号：TASK + yyMMdd + 随机码")
    private String bizNo;

    @Schema(description = "名称")
    private String name;

    @Schema(description = "产线代码")
    private String line;

    @Schema(description = "状态：draft/pending/processing/waitreview/quality/collected/reject")
    private String status;

    @Schema(description = "优先级：high/mid/low")
    private String priority;

    @Schema(description = "图文融合任务大类：几何/统计/表格/示意")
    private String imageClass;

    @Schema(description = "素材批次内部主键")
    private Long batchId;

    @Schema(description = "创建时锁定的参数版本号")
    private String paramVersion;

    @Schema(description = "参数快照 JSON")
    private String paramSnapshot;

    @Schema(description = "任务级置信度阈值")
    private BigDecimal threshold;

    @Schema(description = "当前执行环节号 1-3（0=未开始）")
    private Integer currentStage;

    @Schema(description = "创建人展示名")
    private String createBy;

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
