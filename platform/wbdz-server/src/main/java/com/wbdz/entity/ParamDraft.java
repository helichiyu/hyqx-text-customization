package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 参数配置草稿（每产线一份，发布后清除）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_param_draft", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class ParamDraft {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    /** formula / layout / graphic / metadata / common。 */
    private String line;

    /** 参数组 JSON：[{name,value,desc}]。 */
    private String content;

    private String updateBy;

    private LocalDateTime updateTime;
}
