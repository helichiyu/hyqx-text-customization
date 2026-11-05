package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 数据集版本（任务归集生成）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_dataset", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "数据集版本")
public class Dataset implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    /** DS + yyMMdd + 随机码。 */
    @Schema(description = "业务编号")
    private String bizNo;

    @Schema(description = "产线代码")
    private String line;

    @Schema(description = "任务内部主键")
    private Long taskId;

    /** 最终条数 = 成功 - C 剔除。 */
    @Schema(description = "条目数")
    private Integer itemCount;

    /** C 剔除条数（报告展示用）。 */
    @Schema(description = "剔除条数")
    private Integer skipCount;

    /** 语义版本：V1.0 产线直出 / V2.0 复核闭环 / V3.0 起每重跑 +1。 */
    @Schema(description = "语义版本号")
    private String semVer;

    /** candidate/published/rolledback。 */
    @Schema(description = "状态")
    private String status;

    @Schema(description = "发布人")
    private String publishBy;

    @Schema(description = "发布时间")
    private LocalDateTime publishTime;

    @Schema(description = "创建人")
    private String createBy;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    @Schema(description = "回滚时间")
    private LocalDateTime rollbackTime;
}
