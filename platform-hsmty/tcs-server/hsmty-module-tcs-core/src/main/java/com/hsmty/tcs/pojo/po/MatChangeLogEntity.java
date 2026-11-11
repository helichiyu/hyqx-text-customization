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
import java.time.LocalDateTime;

/**
 * <p>素材批次基本信息变更记录（只读留痕）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_mat_change_log", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "素材批次变更记录")
public class MatChangeLogEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "素材批次内部主键")
    private Long batchId;

    @Schema(description = "变更项：name/line")
    private String item;

    @Schema(description = "变更前值")
    private String oldValue;

    @Schema(description = "变更后值")
    private String newValue;

    @Schema(description = "操作人")
    private String operator;

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
