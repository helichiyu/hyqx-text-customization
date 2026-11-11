package com.hsmty.tcs.pojo.vo;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * <p>数据集条目加入复核后的结果。
 *
 * @param orderId    复核单内部主键
 * @param orderBizNo 复核单业务编号
 * @author helichiyu
 * @since 2.0.1
 */
@Schema(description = "加入复核结果")
public record ReviewAddResultVO(
        @Schema(description = "复核单内部主键") Long orderId,
        @Schema(description = "复核单业务编号") String orderBizNo) {
}
