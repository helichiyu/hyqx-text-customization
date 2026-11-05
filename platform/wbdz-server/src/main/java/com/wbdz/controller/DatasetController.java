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

    @Operation(summary = "分页查询数据集")
    @GetMapping
    public ApiResult<PageResult<DatasetVO>> page(@RequestParam(required = false) String line,
                                                 @RequestParam(required = false) String status,
                                                 @RequestParam(required = false) String keyword,
                                                 @RequestParam(defaultValue = "1") int pageNum,
                                                 @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.page(line, status, keyword, pageNum, pageSize));
    }

    @Operation(summary = "按业务编号查询数据集详情")
    @GetMapping("/by-no/{bizNo}")
    public ApiResult<DatasetDetailVO> detailByBizNo(@PathVariable String bizNo,
                                                    @RequestParam(required = false) String reviewStatus,
                                                    @RequestParam(defaultValue = "1") int pageNum,
                                                    @RequestParam(defaultValue = "10") int pageSize) {
        return detail(bizNo, reviewStatus, pageNum, pageSize);
    }

    @Operation(summary = "查询数据集详情")
    @GetMapping("/{reference}")
    public ApiResult<DatasetDetailVO> detail(@PathVariable String reference,
                                             @RequestParam(required = false) String reviewStatus,
                                             @RequestParam(defaultValue = "1") int pageNum,
                                             @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.detail(datasetService.resolveId(reference),
                reviewStatus, pageNum, pageSize));
    }

    @Operation(summary = "发布数据集")
    @PostMapping("/{reference}/publish")
    public ApiResult<DatasetVO> publish(@PathVariable String reference) {
        return ApiResult.success(datasetService.publish(datasetService.resolveId(reference)));
    }

    @Operation(summary = "回滚数据集")
    @PostMapping("/{reference}/rollback")
    public ApiResult<DatasetVO> rollback(@PathVariable String reference,
                                         @RequestBody @Valid DatasetRollbackDTO dto) {
        return ApiResult.success(datasetService.rollback(datasetService.resolveId(reference), dto.reason()));
    }

    @Operation(summary = "下载数据集质量报告")
    @GetMapping("/{reference}/report")
    public ResponseEntity<byte[]> report(@PathVariable String reference) {
        DatasetService.ReportFile file = datasetService.report(datasetService.resolveId(reference));
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment()
                                .filename(file.filename(), StandardCharsets.UTF_8).build().toString())
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(file.bytes());
    }

    @Operation(summary = "分页查询交付记录")
    @GetMapping("/deliveries")
    public ApiResult<PageResult<DatasetDeliveryRowVO>> deliveries(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.deliveries(pageNum, pageSize));
    }
}