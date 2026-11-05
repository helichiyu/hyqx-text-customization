package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.dto.ParamSaveDTO;
import com.wbdz.service.ParamService;
import com.wbdz.vo.ParamLineConfigVO;
import com.wbdz.vo.ParamOverviewVO;
import com.wbdz.vo.ParamVersionVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
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

/**
 * 参数配置接口。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Tag(name = "参数配置", description = "参数草稿、发布版本和产线配置查询")
@RestController
@RequestMapping("/api/param")
@RequiredArgsConstructor
public class ParamController {

    private final ParamService paramService;

    /** 各产线最新版本概览。 */
    @Operation(summary = "查询参数版本概览")
    @GetMapping("/overview")
    public ApiResult<List<ParamOverviewVO>> overview() {
        return ApiResult.success(paramService.overview());
    }

    /** 产线配置页数据（最新版本 + 草稿 + 历史版本）。 */
    @Operation(summary = "查询产线参数配置")
    @GetMapping("/{line}")
    public ApiResult<ParamLineConfigVO> lineConfig(@PathVariable String line) {
        return ApiResult.success(paramService.lineConfig(line));
    }

    /** 保存草稿。 */
    @Operation(summary = "保存参数草稿")
    @PutMapping("/{line}/draft")
    public ApiResult<Void> saveDraft(@PathVariable String line, @RequestBody @Valid ParamSaveDTO dto) {
        paramService.saveDraft(line, dto.content());
        return ApiResult.success();
    }

    /** 发布新版本（版本号自增，草稿清除）。 */
    @Operation(summary = "发布参数版本")
    @PostMapping("/{line}/publish")
    public ApiResult<ParamVersionVO> publish(@PathVariable String line,
                                             @RequestBody(required = false) @Valid ParamSaveDTO dto) {
        return ApiResult.success(paramService.publish(line, dto == null ? null : dto.content()));
    }
}