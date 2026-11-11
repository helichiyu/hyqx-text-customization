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
 * <p>数据集交付记录。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_delivery_log", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "交付记录")
public class DeliveryLogEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "业务编号：DL + yyMMdd + 随机码")
    private String bizNo;

    @Schema(description = "数据集内部主键")
    private Long datasetId;

    @Schema(description = "交付类型：report/dataset")
    private String type;

    @Schema(description = "交付文件名")
    private String filename;

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
