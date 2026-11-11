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
 * <p>素材批次。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Table(value = "tcs_mat_batch", onInsert = EntityChangeListener.class, onUpdate = EntityChangeListener.class)
@Schema(description = "素材批次")
public class MatBatchEntity implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = SzIdGenerator.NAME)
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "业务编号：产线前缀（GS/FZ/TW/YX）+ yyMMdd + 随机码")
    private String bizNo;

    @Schema(description = "名称")
    private String name;

    @Schema(description = "产线代码：formula/layout/graphic/metadata")
    private String line;

    @Schema(description = "状态：uncheked/checked/released/upload_failed")
    private String status;

    @Schema(description = "有效素材条数（剔除后）")
    private Integer fileCount;

    @Schema(description = "原始文件数")
    private Integer totalCount;

    @Schema(description = "剔除情况汇总 JSON：[{reason,count}]")
    private String rejectSummary;

    @Schema(description = "上传人展示名")
    private String createBy;

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
