package com.wbdz.vo;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 服务健康状态。
 *
 * @param service 服务名
 * @author wbdz
 * @since 2026-11-05
 */
@Schema(description = "服务健康状态")
public record HealthVO(@Schema(description = "服务名") String service) {
}