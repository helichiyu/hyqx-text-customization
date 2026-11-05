package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.util.List;

/**
 * 素材批次详情聚合响应。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "素材批次详情聚合响应")
public class MaterialDetailVO extends MaterialVO {

    @Schema(description = "文件级校验结果")
    private List<FileItem> files;
    @Schema(description = "批次变更记录")
    private List<ChangeItem> changes;
    @Schema(description = "关联的非草稿任务内部主键")
    private List<Long> linkedTaskIds;

    @Data
    @Schema(description = "素材文件校验结果")
    public static class FileItem {
        @Schema(description = "文件名")
        private String name;
        @Schema(description = "扩展名")
        private String ext;
        @Schema(description = "文件大小，单位字节")
        private Long sizeBytes;
        @Schema(description = "PDF 页数")
        private Integer pageCount;
        @Schema(description = "文件校验状态")
        private String status;
        @Schema(description = "剔除原因")
        private String rejectReason;
    }

    @Data
    @Schema(description = "素材批次变更记录")
    public static class ChangeItem {
        @Schema(description = "变更项")
        private String item;
        @Schema(description = "变更前")
        private String oldValue;
        @Schema(description = "变更后")
        private String newValue;
        @Schema(description = "操作人")
        private String operator;
        @Schema(description = "操作时间")
        private String time;
    }
}