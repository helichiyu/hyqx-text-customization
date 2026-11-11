package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * <p>参数版本概览行。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Schema(description = "参数版本概览行")
public class ParamOverviewVO {

    @Schema(description = "产线代码")
    private String line;

    @Schema(description = "产线中文名")
    private String lineName;

    @Schema(description = "最新版本号")
    private String version;

    @Schema(description = "发布时间")
    private String publishedAt;
}
