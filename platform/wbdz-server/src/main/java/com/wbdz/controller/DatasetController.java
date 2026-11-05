package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.PageResult;
import com.wbdz.dto.DatasetRollbackDTO;
import com.wbdz.service.DatasetService;
import com.wbdz.vo.DatasetDeliveryRowVO;
import com.wbdz.vo.DatasetDetailVO;
import com.wbdz.vo.DatasetVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;

/**
 * 数据集管理接口。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Tag(name = "数据集管理", description = "数据集查询、发布、回滚、报告与交付记录")
@RestController
@RequestMapping("/api/dataset")
@RequiredArgsConstructor
public class DatasetController {

    private final DatasetService datasetService;

    /** 数据集分页。 */
    @Operation(summary = "分页查询数据集")
    @GetMapping
    public ApiResult<PageResult<DatasetVO>> page(@RequestParam(required = false) String line,
                                                 @RequestParam(required = false) String status,
                                                 @RequestParam(required = false) String keyword,
                                                 @RequestParam(defaultValue = "1") int pageNum,
                                                 @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.page(line, status, keyword, pageNum, pageSize));
    }

    /** 数据集详情（含明细分页与交付/回滚记录）。 */
    @Operation(summary = "查询数据集详情")
    @GetMapping("/{id}")
    public ApiResult<DatasetDetailVO> detail(@PathVariable Long id,
                                             @RequestParam(required = false) String reviewStatus,
                                             @RequestParam(defaultValue = "1") int pageNum,
                                             @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.detail(id, reviewStatus, pageNum, pageSize));
    }

    /** 发布（候选 → 已发布，复核单须全部闭环）。 */
    @Operation(summary = "发布数据集")
    @PostMapping("/{id}/publish")
    public ApiResult<DatasetVO> publish(@PathVariable Long id) {
        return ApiResult.success(datasetService.publish(id));
    }

    /** 回滚（原因必填留痕）。 */
    @Operation(summary = "回滚数据集")
    @PostMapping("/{id}/rollback")
    public ApiResult<DatasetVO> rollback(@PathVariable Long id,
                                         @RequestBody @Valid DatasetRollbackDTO dto) {
        return ApiResult.success(datasetService.rollback(id, dto.reason()));
    }

    /** 质量报告 TXT 下载（仅已发布；记录交付）。 */
    @Operation(summary = "下载数据集质量报告")
    @GetMapping("/{id}/report")
    public ResponseEntity<byte[]> report(@PathVariable Long id) {
        DatasetService.ReportFile file = datasetService.report(id);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment()
                                .filename(file.filename(), StandardCharsets.UTF_8).build().toString())
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(file.bytes());
    }

    /** 交付记录分页。 */
    @Operation(summary = "分页查询交付记录")
    @GetMapping("/deliveries")
    public ApiResult<PageResult<DatasetDeliveryRowVO>> deliveries(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.deliveries(pageNum, pageSize));
    }
}