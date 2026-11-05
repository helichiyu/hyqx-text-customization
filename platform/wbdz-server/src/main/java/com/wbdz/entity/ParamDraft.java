package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 参数配置草稿（每产线一份，发布后清除）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_param_draft", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "参数配置草稿")
public class ParamDraft implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    /** formula / layout / graphic / metadata / common。 */
    @Schema(description = "产线代码")
    private String line;

    /** 参数组 JSON：[{name,value,desc}]。 */
    @Schema(description = "JSON 内容")
    private String content;

    @Schema(description = "更新人")
    private String updateBy;

    @Schema(description = "更新时间")
    private LocalDateTime updateTime;
}
