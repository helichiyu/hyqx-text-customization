package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 素材批次基本信息变更记录（只读留痕）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_mat_change_log", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "素材批次变更记录")
public class MatChangeLog implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "素材批次内部主键")
    private Long batchId;

    /** name / line。 */
    @Schema(description = "变更项")
    private String item;

    @Schema(description = "变更前值")
    private String oldValue;

    @Schema(description = "变更后值")
    private String newValue;

    @Schema(description = "操作人")
    private String operator;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
