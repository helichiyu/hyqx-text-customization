package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 参数配置版本（按产线发布；任务创建锁定快照）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_param_version", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class ParamVersion {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    /** formula / layout / graphic / metadata / common（素材准入规则）。 */
    private String line;

    /** v1.0 / v1.1 ... */
    private String version;

    /** 参数组 JSON：[{name,value,desc}]。 */
    private String content;

    private LocalDateTime publishedAt;

    private String publishedBy;
}
