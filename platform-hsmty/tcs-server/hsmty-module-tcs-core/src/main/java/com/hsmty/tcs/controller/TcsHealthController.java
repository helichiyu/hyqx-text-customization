package com.hsmty.tcs.controller;

import com.hsmty.core.common.entity.ApiResult;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * <p>文本定制化生产模块健康检查接口。
 *
 * <p>路径为 {@code /hs-api/tcs/health}，用于容器探针和联调探活。
 * 该接口登记在 {@code router.whitelist} 中，属于显式开放的免鉴权接口，
 * 因此不添加 {@code @PreAuthorize}。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Tag(name = "健康检查")
@RestController
@RequestMapping("health")
@RequiredArgsConstructor
public class TcsHealthController {

    /**
     * <p>模块健康检查。
     *
     * @return 统一成功响应
     */
    @Operation(summary = "健康检查（白名单开放，用于容器探针与联调）")
    @GetMapping
    public ApiResult<Void> health() {
        return ApiResult.success();
    }
}
