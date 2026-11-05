package com.wbdz.vo;

import com.wbdz.common.JsonUtil;
import com.wbdz.entity.MatBatch;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 素材批次基础信息。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@Schema(description = "素材批次基础信息")
public class MaterialVO {

    @Schema(description = "素材批次内部主键")
    private Long id;
    @Schema(description = "素材批次业务编号")
    private String bizNo;
    @Schema(description = "素材批次名称")
    private String name;
    @Schema(description = "产线代码")
    private String line;
    @Schema(description = "产线中文名")
    private String lineName;
    @Schema(description = "批次状态")
    private String status;
    @Schema(description = "有效素材条数")
    private Integer fileCount;
    @Schema(description = "原始文件数")
    private Integer totalCount;
    @Schema(description = "剔除情况汇总")
    private List<Map<String, Object>> rejectSummary;
    @Schema(description = "创建人")
    private String createBy;
    @Schema(description = "创建时间")
    private String createTime;

    public static MaterialVO from(MatBatch batch) {
        MaterialVO vo = new MaterialVO();
        vo.setId(batch.getId());
        vo.setBizNo(batch.getBizNo());
        vo.setName(batch.getName());
        vo.setLine(batch.getLine());
        vo.setStatus(batch.getStatus());
        vo.setFileCount(batch.getFileCount());
        vo.setTotalCount(batch.getTotalCount());
        vo.setRejectSummary(batch.getRejectSummary() == null ? List.of() : JsonUtil.readList(batch.getRejectSummary()));
        vo.setCreateBy(batch.getCreateBy());
        vo.setCreateTime(String.valueOf(batch.getCreateTime()));
        return vo;
    }
}