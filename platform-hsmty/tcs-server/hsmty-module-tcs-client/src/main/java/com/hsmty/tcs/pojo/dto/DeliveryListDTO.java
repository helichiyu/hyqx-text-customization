package com.hsmty.tcs.pojo.dto;

import com.hsmty.core.common.entity.PageQuery;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * <p>交付记录分页查询入参。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@EqualsAndHashCode(callSuper = true)
@Schema(description = "交付记录分页查询入参")
public class DeliveryListDTO extends PageQuery {
}
