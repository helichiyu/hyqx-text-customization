package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 交付记录（质量报告下载等）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_delivery_log", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "数据集交付记录")
public class DeliveryLog implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    /** 产线前缀业务编号。 */
    @Schema(description = "业务编号")
    private String bizNo;

    @Schema(description = "数据集内部主键")
    private Long datasetId;

    /** 交付类型（质量报告下载）。 */
    @Schema(description = "类型")
    private String type;

    @Schema(description = "文件名")
    private String filename;

    @Schema(description = "操作人")
    private String operator;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
