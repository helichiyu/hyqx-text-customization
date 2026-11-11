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
 * <p>参数配置版本（按产线发布；任务创建锁定快照）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_param_version", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "参数配置版本")
public class ParamVersionEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "产线代码：formula/layout/graphic/metadata/common")
    private String line;

    @Schema(description = "版本号：v1.0 / v1.1 ...")
    private String version;

    @Schema(description = "参数组 JSON：[{name,value,desc}]")
    private String content;

    @Schema(description = "发布时间")
    private LocalDateTime publishedAt;

    @Schema(description = "发布人")
    private String publishedBy;

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
