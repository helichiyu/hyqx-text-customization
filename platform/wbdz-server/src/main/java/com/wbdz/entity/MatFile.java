package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 素材文件（批次内明细）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_mat_file", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "素材文件校验记录")
public class MatFile implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "素材批次内部主键")
    private Long batchId;

    @Schema(description = "名称")
    private String name;

    @Schema(description = "扩展名")
    private String ext;

    @Schema(description = "文件大小，单位字节")
    private Long sizeBytes;

    @Schema(description = "文件 SHA-256")
    private String sha256;

    /** PDF 页数（按页计数的产线使用）。 */
    @Schema(description = "PDF 页数")
    private Integer pageCount;

    /** passed / rejected。 */
    @Schema(description = "状态")
    private String status;

    /** 剔除原因（中文）。 */
    @Schema(description = "剔除原因")
    private String rejectReason;

    /** 平台存储相对路径。 */
    @Schema(description = "存储相对路径")
    private String storePath;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
