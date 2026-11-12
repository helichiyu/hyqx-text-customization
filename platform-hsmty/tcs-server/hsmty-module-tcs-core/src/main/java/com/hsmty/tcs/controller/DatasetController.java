package com.hsmty.tcs.controller;

import com.hsmty.core.common.entity.ApiPageResult;
import com.hsmty.core.common.entity.ApiResult;
import com.hsmty.core.common.entity.PageResult;
import com.hsmty.tcs.pojo.dto.DatasetDetailDTO;
import com.hsmty.tcs.pojo.dto.DatasetListDTO;
import com.hsmty.tcs.pojo.dto.DatasetRollbackDTO;
import com.hsmty.tcs.pojo.dto.DeliveryListDTO;
import com.hsmty.tcs.pojo.vo.DatasetDeliveryRowVO;
import com.hsmty.tcs.pojo.vo.DatasetDetailVO;
import com.hsmty.tcs.pojo.vo.DatasetVO;
import com.hsmty.tcs.service.DatasetService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;

/**
 * <p>数据集管理接口。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Tag(name = "数据集管理", description = "数据集查询、发布、回滚、报告与交付记录")
@RestController
@RequestMapping("dataset")
@RequiredArgsConstructor
public class DatasetController {

    private final DatasetService datasetService;

    /**
     * <p>分页查询数据集。
     */
    @Operation(summary = "分页查询数据集")
    @PreAuthorize("hasAnyAuthority('tcs:dataset:page')")
    @GetMapping
    public ApiResult<PageResult<DatasetVO>> page(DatasetListDTO dto) {
        return ApiPageResult.success(datasetService.page(dto));
    }

    /**
     * <p>查询数据集详情。
     */
    @Operation(summary = "查询数据集详情（支持 ID 或业务编号）")
    @PreAuthorize("hasAnyAuthority('tcs:dataset:detail')")
    @GetMapping("/{reference}")
    public ApiResult<DatasetDetailVO> detail(@PathVariable String reference, DatasetDetailDTO dto) {
        return ApiResult.success(datasetService.detail(datasetService.resolveId(reference), dto));
    }

    /**
     * <p>发布数据集。
     */
    @Operation(summary = "发布数据集")
    @PreAuthorize("hasAnyAuthority('tcs:dataset:publish')")
    @PostMapping("/{reference}/publish")
    public ApiResult<DatasetVO> publish(@PathVariable String reference) {
        return ApiResult.success(datasetService.publish(datasetService.resolveId(reference)));
    }

    /**
     * <p>回滚数据集。
     */
    @Operation(summary = "回滚数据集")
    @PreAuthorize("hasAnyAuthority('tcs:dataset:rollback')")
    @PostMapping("/{reference}/rollback")
    public ApiResult<DatasetVO> rollback(@PathVariable String reference,
                                         @RequestBody @Valid DatasetRollbackDTO dto) {
        return ApiResult.success(datasetService.rollback(datasetService.resolveId(reference), dto.reason()));
    }

    /**
     * <p>下载数据集质量报告（TXT）。
     */
    @Operation(summary = "下载数据集质量报告")
    @PreAuthorize("hasAnyAuthority('tcs:dataset:report')")
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

    /**
     * <p>分页查询交付记录。
     */
    @Operation(summary = "分页查询交付记录")
    @PreAuthorize("hasAnyAuthority('tcs:dataset:delivery')")
    @GetMapping("/deliveries")
    public ApiResult<PageResult<DatasetDeliveryRowVO>> deliveries(DeliveryListDTO dto) {
        return ApiPageResult.success(datasetService.deliveries(dto));
    }

    /**
     * <p>删除数据集（逻辑删除，级联删除条目）；已发布数据集须先回滚。
     */
    @Operation(summary = "删除数据集")
    @PreAuthorize("hasAnyAuthority('tcs:dataset:remove')")
    @DeleteMapping("/{reference}")
    public ApiResult<Void> delete(@PathVariable String reference) {
        datasetService.remove(datasetService.resolveId(reference));
        return ApiResult.success();
    }
}
