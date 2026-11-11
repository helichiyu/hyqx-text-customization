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
 * <p>参数配置草稿（每产线一份，发布后清除）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_param_draft", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "参数配置草稿")
public class ParamDraftEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "产线代码或 common")
    private String line;

    @Schema(description = "参数组 JSON：[{name,value,desc}]")
    private String content;

    @Schema(description = "最近编辑人展示名")
    private String updateBy;

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
