package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 参数配置版本（按产线发布；任务创建锁定快照）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_param_version", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "参数配置版本")
public class ParamVersion implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    /** formula / layout / graphic / metadata / common（素材准入规则）。 */
    @Schema(description = "产线代码")
    private String line;

    /** v1.0 / v1.1 ... */
    @Schema(description = "版本号")
    private String version;

    /** 参数组 JSON：[{name,value,desc}]。 */
    @Schema(description = "JSON 内容")
    private String content;

    @Schema(description = "发布时间")
    private LocalDateTime publishedAt;

    @Schema(description = "发布人")
    private String publishedBy;
}
