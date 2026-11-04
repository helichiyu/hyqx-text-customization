package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.PageResult;
import com.wbdz.dto.MaterialEditDTO;
import com.wbdz.entity.MatBatch;
import com.wbdz.service.MaterialService;
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
import java.util.Map;

/**
 * 素材管理接口。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@RestController
@RequestMapping("/api/material")
@RequiredArgsConstructor
public class MaterialController {

    private final MaterialService materialService;

    /** 上传素材批次（文件与 ZIP 混合；服务端解包并完成文件级校验）。 */
    @PostMapping("/upload")
    public ApiResult<MatBatch> upload(@RequestParam String line,
                                      @RequestParam String name,
                                      @RequestParam("files") List<MultipartFile> files) {
        return ApiResult.success(materialService.upload(line, name, files));
    }

    /** 批次分页列表（支持产线/名称/状态筛选，含派生态「已关联」）。 */
    @GetMapping
    public ApiResult<PageResult<Map<String, Object>>> page(@RequestParam(required = false) String line,
                                                           @RequestParam(required = false) String name,
                                                           @RequestParam(required = false) String status,
                                                           @RequestParam(defaultValue = "1") int pageNum,
                                                           @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(materialService.page(line, name, status, pageNum, pageSize));
    }

    /** 批次详情：基本信息 + 文件清单（剔除情况）+ 变更记录 + 关联任务。 */
    @GetMapping("/{id}")
    public ApiResult<Map<String, Object>> detail(@PathVariable Long id) {
        return ApiResult.success(materialService.detail(id));
    }

    /** 准入校验（未校验 → 已校验 / 上传失败）。 */
    @PostMapping("/{id}/check")
    public ApiResult<MatBatch> check(@PathVariable Long id) {
        return ApiResult.success(materialService.check(id));
    }

    /** 移交（已校验 → 已移交）。 */
    @PostMapping("/{id}/release")
    public ApiResult<MatBatch> release(@PathVariable Long id) {
        return ApiResult.success(materialService.release(id));
    }

    /** 编辑基本信息（名称/产线）。 */
    @PutMapping("/{id}")
    public ApiResult<MatBatch> edit(@PathVariable Long id, @RequestBody MaterialEditDTO dto) {
        return ApiResult.success(materialService.edit(id, dto.name(), dto.line()));
    }

    /** 删除批次（已移交/已关联不可删）。 */
    @DeleteMapping("/{id}")
    public ApiResult<Void> delete(@PathVariable Long id) {
        materialService.delete(id);
        return ApiResult.success();
    }
}
