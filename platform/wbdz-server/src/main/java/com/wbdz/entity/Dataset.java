package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 数据集版本（任务归集生成）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_dataset", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class Dataset {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    /** DS + yyMMdd + 随机码。 */
    private String bizNo;

    private String line;

    private Long taskId;

    /** 最终条数 = 成功 - C 剔除。 */
    private Integer itemCount;

    /** C 剔除条数（报告展示用）。 */
    private Integer skipCount;

    /** 语义版本：V1.0 产线直出 / V2.0 复核闭环 / V3.0 起每重跑 +1。 */
    private String semVer;

    /** candidate/published/rolledback。 */
    private String status;

    private String publishBy;

    private LocalDateTime publishTime;

    private String createBy;

    private LocalDateTime createTime;

    private LocalDateTime rollbackTime;
}
