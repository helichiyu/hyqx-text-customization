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
 * <p>素材文件（批次内明细）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_mat_file", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "素材文件校验记录")
public class MatFileEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
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

    @Schema(description = "PDF 页数")
    private Integer pageCount;

    @Schema(description = "状态：passed/rejected")
    private String status;

    @Schema(description = "剔除原因")
    private String rejectReason;

    @Schema(description = "平台存储相对路径")
    private String storePath;

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
