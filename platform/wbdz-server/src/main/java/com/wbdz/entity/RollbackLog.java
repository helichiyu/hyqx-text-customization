package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 数据集回滚记录（原因必填留痕）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_rollback_log", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class RollbackLog {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    /** 产线前缀业务编号。 */
    private String bizNo;

    private Long datasetId;

    /** 回滚目标数据集业务编号或「下线」。 */
    private String target;

    private String reason;

    private String operator;

    private LocalDateTime createTime;
}
