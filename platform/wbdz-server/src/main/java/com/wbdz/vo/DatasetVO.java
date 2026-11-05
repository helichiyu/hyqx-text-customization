package com.wbdz.vo;

import com.wbdz.entity.Dataset;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 数据集基础信息。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@Schema(description = "数据集基础信息")
public class DatasetVO {
    @Schema(description = "数据集内部主键")
    private Long id;
    @Schema(description = "数据集业务编号")
    private String bizNo;
    @Schema(description = "产线代码")
    private String line;
    @Schema(description = "产线中文名")
    private String lineName;
    @Schema(description = "来源任务内部主键")
    private Long taskId;
    @Schema(description = "最终条数")
    private Integer itemCount;
    @Schema(description = "剔除条数")
    private Integer skipCount;
    @Schema(description = "语义版本号")
    private String semVer;
    @Schema(description = "数据集状态")
    private String status;
    @Schema(description = "数据集状态中文名")
    private String statusName;
    @Schema(description = "发布人")
    private String publishBy;
    @Schema(description = "发布时间")
    private String publishTime;
    @Schema(description = "创建时间")
    private String createTime;

    public static DatasetVO from(Dataset dataset) {
        DatasetVO vo = new DatasetVO();
        vo.setId(dataset.getId());
        vo.setBizNo(dataset.getBizNo());
        vo.setLine(dataset.getLine());
        vo.setTaskId(dataset.getTaskId());
        vo.setItemCount(dataset.getItemCount());
        vo.setSkipCount(dataset.getSkipCount());
        vo.setSemVer(dataset.getSemVer());
        vo.setStatus(dataset.getStatus());
        vo.setPublishBy(dataset.getPublishBy());
        vo.setPublishTime(String.valueOf(dataset.getPublishTime()));
        vo.setCreateTime(String.valueOf(dataset.getCreateTime()));
        return vo;
    }
}