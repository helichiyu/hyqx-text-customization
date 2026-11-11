package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Map;

/**
 * <p>复核条目。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@Schema(description = "复核条目")
public class ReviewItemVO {

    @Schema(description = "条目内部主键")
    private Long id;

    @Schema(description = "复核单内部主键")
    private Long orderId;

    @Schema(description = "数据集行标识")
    private String itemKey;

    @Schema(description = "触发原因分类码")
    private String code;

    @Schema(description = "触发原因描述")
    private String reason;

    @Schema(description = "算子原始行")
    private Map<String, Object> payload;

    @Schema(description = "复核结论：A/B/C")
    private String conclusion;

    @Schema(description = "修正前字段值")
    private Map<String, Object> beforeValue;

    @Schema(description = "修正后字段值")
    private Map<String, Object> afterValue;

    @Schema(description = "复核操作人")
    private String operator;

    @Schema(description = "结论时间")
    private String concludeTime;
}
