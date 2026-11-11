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
 * <p>数据集（一次环节产出即一份数据集，版本号形如 V1.0）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_dataset", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "数据集")
public class DatasetEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "业务编号：DS + yyMMdd + 随机码")
    private String bizNo;

    @Schema(description = "产线代码")
    private String line;

    @Schema(description = "任务内部主键")
    private Long taskId;

    @Schema(description = "条目数")
    private Integer itemCount;

    @Schema(description = "跳过条目数")
    private Integer skipCount;

    @Schema(description = "语义化版本号，如 V1.0")
    private String semVer;

    @Schema(description = "状态：unreleased/released")
    private String status;

    @Schema(description = "发布操作人")
    private String publishBy;

    @Schema(description = "发布时间")
    private LocalDateTime publishTime;

    @Schema(description = "创建人展示名")
    private String createBy;

    @Schema(description = "回滚时间")
    private LocalDateTime rollbackTime;

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
