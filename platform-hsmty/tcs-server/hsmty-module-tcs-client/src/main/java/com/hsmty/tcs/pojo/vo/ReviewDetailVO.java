package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.util.List;

/**
 * <p>复核单详情聚合响应。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "复核单详情聚合响应")
public class ReviewDetailVO extends ReviewOrderVO {

    @Schema(description = "复核条目")
    private List<ReviewItemVO> items;

    @Schema(description = "来源执行记录内部主键")
    private Long runId;

    @Schema(description = "来源图片执行记录内部主键")
    private Long imageRunId;
}
