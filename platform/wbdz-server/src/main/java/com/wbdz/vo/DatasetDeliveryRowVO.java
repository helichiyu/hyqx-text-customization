package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 交付记录列表行。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@Schema(description = "交付记录列表行")
public class DatasetDeliveryRowVO {
    @Schema(description = "交付记录业务编号")
    private String bizNo;
    @Schema(description = "数据集内部主键")
    private Long datasetId;
    @Schema(description = "数据集业务编号")
    private String datasetBizNo;
    @Schema(description = "产线中文名")
    private String lineName;
    @Schema(description = "交付类型")
    private String type;
    @Schema(description = "文件名")
    private String filename;
    @Schema(description = "操作人")
    private String operator;
    @Schema(description = "交付时间")
    private String time;
}