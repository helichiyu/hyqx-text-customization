package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 数据集回滚记录（原因必填留痕）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_rollback_log", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "数据集回滚记录")
public class RollbackLog implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    /** 产线前缀业务编号。 */
    @Schema(description = "业务编号")
    private String bizNo;

    @Schema(description = "数据集内部主键")
    private Long datasetId;

    /** 回滚目标数据集业务编号或「下线」。 */
    @Schema(description = "操作目标")
    private String target;

    @Schema(description = "原因")
    private String reason;

    @Schema(description = "操作人")
    private String operator;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
