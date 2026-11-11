package com.hsmty.tcs.controller;

import com.hsmty.core.common.entity.ApiResult;
import com.hsmty.tcs.pojo.dto.ParamSaveDTO;
import com.hsmty.tcs.pojo.vo.ParamLineConfigVO;
import com.hsmty.tcs.pojo.vo.ParamOverviewVO;
import com.hsmty.tcs.pojo.vo.ParamVersionVO;
import com.hsmty.tcs.service.ParamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * <p>参数配置接口。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Tag(name = "参数配置", description = "参数草稿、发布版本和产线配置查询")
@RestController
@RequestMapping("param")
@RequiredArgsConstructor
public class ParamController {

    private final ParamService paramService;

    /**
     * <p>各产线最新版本概览。
     */
    @Operation(summary = "查询参数版本概览")
    @PreAuthorize("hasAnyAuthority('tcs:param:page')")
    @GetMapping("/overview")
    public ApiResult<List<ParamOverviewVO>> overview() {
        return ApiResult.success(paramService.overview());
    }

    /**
     * <p>产线配置页数据（最新版本 + 草稿 + 历史版本）。
     */
    @Operation(summary = "查询产线参数配置")
    @PreAuthorize("hasAnyAuthority('tcs:param:detail')")
    @GetMapping("/{line}")
    public ApiResult<ParamLineConfigVO> lineConfig(@PathVariable String line) {
        return ApiResult.success(paramService.lineConfig(line));
    }

    /**
     * <p>保存草稿。
     */
    @Operation(summary = "保存参数草稿")
    @PreAuthorize("hasAnyAuthority('tcs:param:update')")
    @PutMapping("/{line}/draft")
    public ApiResult<Void> saveDraft(@PathVariable String line, @RequestBody @Valid ParamSaveDTO dto) {
        paramService.saveDraft(line, dto.content());
        return ApiResult.success();
    }

    /**
     * <p>发布新版本（版本号自增，草稿清除）。
     */
    @Operation(summary = "发布参数版本")
    @PreAuthorize("hasAnyAuthority('tcs:param:publish')")
    @PostMapping("/{line}/publish")
    public ApiResult<ParamVersionVO> publish(@PathVariable String line,
                                             @RequestBody(required = false) @Valid ParamSaveDTO dto) {
        return ApiResult.success(paramService.publish(line, dto == null ? null : dto.content()));
    }
}
