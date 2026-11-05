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

    /** 上传素材批次（文件与 ZIP 混合；服务端解包并完成文件级校验）。 */
    @Operation(summary = "上传素材批次")
    @PostMapping("/upload")
    public ApiResult<MaterialVO> upload(@RequestParam String line,
                                        @RequestParam String name,
                                        @RequestParam("files") List<MultipartFile> files) {
        return ApiResult.success(materialService.upload(line, name, files));
    }

    /** 批次分页列表（支持产线/名称/状态筛选，含派生态「已关联」）。 */
    @Operation(summary = "分页查询素材批次")
    @GetMapping
    public ApiResult<PageResult<MaterialRowVO>> page(@RequestParam(required = false) String line,
                                                     @RequestParam(required = false) String name,
                                                     @RequestParam(required = false) String status,
                                                     @RequestParam(defaultValue = "1") int pageNum,
                                                     @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(materialService.page(line, name, status, pageNum, pageSize));
    }

    /** 批次详情：基本信息 + 文件清单（剔除情况）+ 变更记录 + 关联任务。 */
    @Operation(summary = "查询素材批次详情")
    @GetMapping("/{id}")
    public ApiResult<MaterialDetailVO> detail(@PathVariable Long id) {
        return ApiResult.success(materialService.detail(id));
    }

    /** 准入校验（未校验 → 已校验 / 上传失败）。 */
    @Operation(summary = "执行素材准入校验")
    @PostMapping("/{id}/check")
    public ApiResult<MaterialVO> check(@PathVariable Long id) {
        return ApiResult.success(materialService.check(id));
    }

    /** 移交（已校验 → 已移交）。 */
    @Operation(summary = "移交素材批次")
    @PostMapping("/{id}/release")
    public ApiResult<MaterialVO> release(@PathVariable Long id) {
        return ApiResult.success(materialService.release(id));
    }

    /** 编辑基本信息（名称/产线）。 */
    @Operation(summary = "编辑素材批次")
    @PutMapping("/{id}")
    public ApiResult<MaterialVO> edit(@PathVariable Long id, @RequestBody @Valid MaterialEditDTO dto) {
        return ApiResult.success(materialService.edit(id, dto.name(), dto.line()));
    }

    /** 删除批次（已移交/已关联不可删）。 */
    @Operation(summary = "删除素材批次")
    @DeleteMapping("/{id}")
    public ApiResult<Void> delete(@PathVariable Long id) {
        materialService.delete(id);
        return ApiResult.success();
    }
}