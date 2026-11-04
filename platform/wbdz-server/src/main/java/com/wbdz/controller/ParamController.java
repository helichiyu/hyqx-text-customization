package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.dto.ParamSaveDTO;
import com.wbdz.entity.ParamVersion;
import com.wbdz.service.ParamService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 参数配置接口。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@RestController
@RequestMapping("/api/param")
@RequiredArgsConstructor
public class ParamController {

    private final ParamService paramService;

    /** 各产线最新版本概览。 */
    @GetMapping("/overview")
    public ApiResult<List<Map<String, Object>>> overview() {
        return ApiResult.success(paramService.overview());
    }

    /** 产线配置页数据（最新版本 + 草稿 + 历史版本）。 */
    @GetMapping("/{line}")
    public ApiResult<Map<String, Object>> lineConfig(@PathVariable String line) {
        return ApiResult.success(paramService.lineConfig(line));
    }

    /** 保存草稿。 */
    @PutMapping("/{line}/draft")
    public ApiResult<Void> saveDraft(@PathVariable String line, @RequestBody @Valid ParamSaveDTO dto) {
        paramService.saveDraft(line, dto.content());
        return ApiResult.success();
    }

    /** 发布新版本（版本号自增，草稿清除）。 */
    @PostMapping("/{line}/publish")
    public ApiResult<ParamVersion> publish(@PathVariable String line, @RequestBody(required = false) ParamSaveDTO dto) {
        return ApiResult.success(paramService.publish(line, dto == null ? null : dto.content()));
    }
}
