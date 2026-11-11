package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * <p>参数版本。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Schema(description = "参数版本")
public class ParamVersionVO {

    @Schema(description = "产线代码")
    private String line;

    @Schema(description = "参数版本号")
    private String version;

    @Schema(description = "参数组")
    private List<Map<String, Object>> content;

    @Schema(description = "发布时间")
    private String publishedAt;

    @Schema(description = "发布人")
    private String publishedBy;
}
