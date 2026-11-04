package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 平台就绪探针。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@RestController
public class HealthzController {

    @GetMapping("/api/healthz")
    public ApiResult<Map<String, String>> healthz() {
        return ApiResult.success(Map.of("service", "wbdz-server"));
    }
}
