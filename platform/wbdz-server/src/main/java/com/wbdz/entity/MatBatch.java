package com.wbdz.entity;

import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 素材批次。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_mat_batch", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "素材批次")
public class MatBatch implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    /** 业务编号：产线前缀（GS/FZ/TW/YX）+ yyMMdd + 随机码。 */
    @Schema(description = "业务编号")
    private String bizNo;

    @Schema(description = "名称")
    private String name;

    /** formula / layout / graphic / metadata。 */
    @Schema(description = "产线代码")
    private String line;

    /** uncheked / checked / released / upload_failed；已关联为派生态（被非草稿任务引用）。 */
    @Schema(description = "状态")
    private String status;

    /** 有效素材条数（剔除后）。 */
    @Schema(description = "有效文件数")
    private Integer fileCount;

    /** 原始文件数。 */
    @Schema(description = "原始文件数")
    private Integer totalCount;

    /** 剔除情况汇总 JSON：[{reason,count}]。 */
    @Schema(description = "剔除汇总 JSON")
    private String rejectSummary;

    @Schema(description = "创建人")
    private String createBy;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    @Schema(description = "更新时间")
    private LocalDateTime updateTime;

    @Column(isLogicDelete = true)
    @Schema(description = "逻辑删除标记")
    private String delFlag;
}
