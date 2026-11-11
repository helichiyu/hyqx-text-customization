package com.hsmty.tcs.controller;

import com.hsmty.core.common.entity.ApiPageResult;
import com.hsmty.core.common.entity.ApiResult;
import com.hsmty.core.common.entity.PageResult;
import com.hsmty.tcs.pojo.dto.MaterialEditDTO;
import com.hsmty.tcs.pojo.dto.MaterialListDTO;
import com.hsmty.tcs.pojo.vo.MaterialDetailVO;
import com.hsmty.tcs.pojo.vo.MaterialRowVO;
import com.hsmty.tcs.pojo.vo.MaterialVO;
import com.hsmty.tcs.service.MaterialService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * <p>素材管理接口。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Tag(name = "素材管理", description = "素材上传、准入校验、移交、编辑与删除")
@RestController
@RequestMapping("material")
@RequiredArgsConstructor
public class MaterialController {

    private final MaterialService materialService;

    /**
     * <p>上传素材批次。
     */
    @Operation(summary = "上传素材批次")
    @PreAuthorize("hasAnyAuthority('tcs:material:create')")
    @PostMapping("/upload")
    public ApiResult<MaterialVO> upload(@RequestParam String line,
                                        @RequestParam String name,
                                        @RequestParam("files") List<MultipartFile> files) {
        return ApiResult.success(materialService.upload(line, name, files));
    }

    /**
     * <p>分页查询素材批次。
     */
    @Operation(summary = "分页查询素材批次")
    @PreAuthorize("hasAnyAuthority('tcs:material:page')")
    @GetMapping
    public ApiResult<PageResult<MaterialRowVO>> page(MaterialListDTO dto) {
        return ApiPageResult.success(materialService.page(dto));
    }

    /**
     * <p>查询素材批次详情。
     */
    @Operation(summary = "查询素材批次详情（支持 ID 或业务编号）")
    @PreAuthorize("hasAnyAuthority('tcs:material:detail')")
    @GetMapping("/{reference}")
    public ApiResult<MaterialDetailVO> detail(@PathVariable String reference) {
        return ApiResult.success(materialService.detail(materialService.resolveId(reference)));
    }

    /**
     * <p>执行素材准入校验。
     */
    @Operation(summary = "执行素材准入校验")
    @PreAuthorize("hasAnyAuthority('tcs:material:check')")
    @PostMapping("/{reference}/check")
    public ApiResult<MaterialVO> check(@PathVariable String reference) {
        return ApiResult.success(materialService.check(materialService.resolveId(reference)));
    }

    /**
     * <p>移交素材批次。
     */
    @Operation(summary = "移交素材批次")
    @PreAuthorize("hasAnyAuthority('tcs:material:release')")
    @PostMapping("/{reference}/release")
    public ApiResult<MaterialVO> release(@PathVariable String reference) {
        return ApiResult.success(materialService.release(materialService.resolveId(reference)));
    }

    /**
     * <p>编辑素材批次。
     */
    @Operation(summary = "编辑素材批次")
    @PreAuthorize("hasAnyAuthority('tcs:material:update')")
    @PutMapping("/{reference}")
    public ApiResult<MaterialVO> edit(@PathVariable String reference,
                                      @RequestBody @Valid MaterialEditDTO dto) {
        return ApiResult.success(materialService.edit(materialService.resolveId(reference), dto));
    }

    /**
     * <p>删除素材批次（逻辑删除）。
     */
    @Operation(summary = "删除素材批次")
    @PreAuthorize("hasAnyAuthority('tcs:material:remove')")
    @DeleteMapping("/{reference}")
    public ApiResult<Void> delete(@PathVariable String reference) {
        materialService.remove(materialService.resolveId(reference));
        return ApiResult.success();
    }
}
