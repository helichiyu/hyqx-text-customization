package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 任务列表行。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "任务列表行")
public class TaskRowVO extends TaskVO {

    @Schema(description = "素材批次业务编号")
    private String batchBizNo;

    @Schema(description = "素材批次名称")
    private String batchName;

    @Schema(description = "关联数据集数量", example = "2")
    private Long datasetCount;
}