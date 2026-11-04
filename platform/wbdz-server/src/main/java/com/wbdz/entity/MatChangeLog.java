package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 素材批次基本信息变更记录（只读留痕）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_mat_change_log", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class MatChangeLog {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    private Long batchId;

    /** name / line。 */
    private String item;

    private String oldValue;

    private String newValue;

    private String operator;

    private LocalDateTime createTime;
}
