package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 素材文件（批次内明细）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_mat_file", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class MatFile {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    private Long batchId;

    private String name;

    private String ext;

    private Long sizeBytes;

    private String sha256;

    /** PDF 页数（按页计数的产线使用）。 */
    private Integer pageCount;

    /** passed / rejected。 */
    private String status;

    /** 剔除原因（中文）。 */
    private String rejectReason;

    /** 平台存储相对路径。 */
    private String storePath;

    private LocalDateTime createTime;
}
