package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 交付记录（质量报告下载等）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_delivery_log", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class DeliveryLog {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    /** 产线前缀业务编号。 */
    private String bizNo;

    private Long datasetId;

    /** 交付类型（质量报告下载）。 */
    private String type;

    private String filename;

    private String operator;

    private LocalDateTime createTime;
}
