package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

/**
 * 产线参数配置页数据。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@Schema(description = "产线参数配置页数据")
public class ParamLineConfigVO {
    @Schema(description = "产线代码")
    private String line;
    @Schema(description = "产线中文名")
    private String lineName;
    @Schema(description = "最新已发布版本")
    private ParamVersionVO latest;
    @Schema(description = "是否存在草稿")
    private Boolean hasDraft;
    @Schema(description = "当前草稿；无草稿时为最新版本")
    private ParamVersionVO draft;
    @Schema(description = "历史发布版本")
    private List<ParamVersionVO> versions;
}