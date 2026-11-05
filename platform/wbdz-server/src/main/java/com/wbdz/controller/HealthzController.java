package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.vo.HealthVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 平台就绪探针。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Tag(name = "健康检查")
@RestController
public class HealthzController {

    @Operation(summary = "查询服务健康状态")
    @GetMapping("/api/healthz")
    public ApiResult<HealthVO> healthz() {
        return ApiResult.success(new HealthVO("wbdz-server"));
    }
}