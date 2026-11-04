package com.wbdz.entity;

import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 素材批次。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_mat_batch", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class MatBatch {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    /** 业务编号：产线前缀（GS/FZ/TW/YX）+ yyMMdd + 随机码。 */
    private String bizNo;

    private String name;

    /** formula / layout / graphic / metadata。 */
    private String line;

    /** uncheked / checked / released / upload_failed；已关联为派生态（被非草稿任务引用）。 */
    private String status;

    /** 有效素材条数（剔除后）。 */
    private Integer fileCount;

    /** 原始文件数。 */
    private Integer totalCount;

    /** 剔除情况汇总 JSON：[{reason,count}]。 */
    private String rejectSummary;

    private String createBy;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;

    @Column(isLogicDelete = true)
    private String delFlag;
}
