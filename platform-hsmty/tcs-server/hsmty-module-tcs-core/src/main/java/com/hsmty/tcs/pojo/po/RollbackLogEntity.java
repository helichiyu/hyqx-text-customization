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
 * <p>数据集回滚记录。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_rollback_log", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "回滚记录")
public class RollbackLogEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "业务编号：RB + yyMMdd + 随机码")
    private String bizNo;

    @Schema(description = "被回滚的数据集内部主键")
    private Long datasetId;

    @Schema(description = "回滚目标（版本号或说明）")
    private String target;

    @Schema(description = "回滚原因")
    private String reason;

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
