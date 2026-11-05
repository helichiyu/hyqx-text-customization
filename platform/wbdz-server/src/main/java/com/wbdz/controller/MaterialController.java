package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.PageResult;
import com.wbdz.dto.MaterialEditDTO;
import com.wbdz.service.MaterialService;
import com.wbdz.vo.MaterialDetailVO;
import com.wbdz.vo.MaterialRowVO;
import com.wbdz.vo.MaterialVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
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
 * 素材管理接口。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Tag(name = "素材管理", description = "素材上传、准入校验、移交、编辑与删除")
@RestController
@RequestMapping("/api/material")
@RequiredArgsConstructor
public class MaterialController {

    private final MaterialService materialService;

    @Operation(summary = "上传素材批次")
    @PostMapping("/upload")
    public ApiResult<MaterialVO> upload(@RequestParam String line,
                                        @RequestParam String name,
                                        @RequestParam("files") List<MultipartFile> files) {
        return ApiResult.success(materialService.upload(line, name, files));
    }

    @Operation(summary = "分页查询素材批次")
    @GetMapping
    public ApiResult<PageResult<MaterialRowVO>> page(@RequestParam(required = false) String line,
                                                     @RequestParam(required = false) String name,
                                                     @RequestParam(required = false) String status,
                                                     @RequestParam(defaultValue = "1") int pageNum,
                                                     @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(materialService.page(line, name, status, pageNum, pageSize));
    }

    @Operation(summary = "按业务编号查询素材批次详情")
    @GetMapping("/by-no/{bizNo}")
    public ApiResult<MaterialDetailVO> detailByBizNo(@PathVariable String bizNo) {
        return detail(bizNo);
    }

    @Operation(summary = "查询素材批次详情")
    @GetMapping("/{reference}")
    public ApiResult<MaterialDetailVO> detail(@PathVariable String reference) {
        return ApiResult.success(materialService.detail(materialService.resolveId(reference)));
    }

    @Operation(summary = "执行素材准入校验")
    @PostMapping("/{reference}/check")
    public ApiResult<MaterialVO> check(@PathVariable String reference) {
        return ApiResult.success(materialService.check(materialService.resolveId(reference)));
    }

    @Operation(summary = "移交素材批次")
    @PostMapping("/{reference}/release")
    public ApiResult<MaterialVO> release(@PathVariable String reference) {
        return ApiResult.success(materialService.release(materialService.resolveId(reference)));
    }

    @Operation(summary = "编辑素材批次")
    @PutMapping("/{reference}")
    public ApiResult<MaterialVO> edit(@PathVariable String reference, @RequestBody @Valid MaterialEditDTO dto) {
        return ApiResult.success(materialService.edit(materialService.resolveId(reference),
                dto.name(), dto.line()));
    }

    @Operation(summary = "删除素材批次")
    @DeleteMapping("/{reference}")
    public ApiResult<Void> delete(@PathVariable String reference) {
        materialService.delete(materialService.resolveId(reference));
        return ApiResult.success();
    }
}