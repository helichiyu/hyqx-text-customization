package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.PageResult;
import com.wbdz.entity.Dataset;
import com.wbdz.service.DatasetService;
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
import java.util.Map;

/**
 * 数据集管理接口。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@RestController
@RequestMapping("/api/dataset")
@RequiredArgsConstructor
public class DatasetController {

    private final DatasetService datasetService;

    /** 数据集分页。 */
    @GetMapping
    public ApiResult<PageResult<Map<String, Object>>> page(@RequestParam(required = false) String line,
                                                           @RequestParam(required = false) String status,
                                                           @RequestParam(required = false) String keyword,
                                                           @RequestParam(defaultValue = "1") int pageNum,
                                                           @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.page(line, status, keyword, pageNum, pageSize));
    }

    /** 数据集详情（含明细分页与交付/回滚记录）。 */
    @GetMapping("/{id}")
    public ApiResult<Map<String, Object>> detail(@PathVariable Long id,
                                                 @RequestParam(required = false) String reviewStatus,
                                                 @RequestParam(defaultValue = "1") int pageNum,
                                                 @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.detail(id, reviewStatus, pageNum, pageSize));
    }

    /** 发布（候选 → 已发布，复核单须全部闭环）。 */
    @PostMapping("/{id}/publish")
    public ApiResult<Dataset> publish(@PathVariable Long id) {
        return ApiResult.success(datasetService.publish(id));
    }

    /** 回滚（body: {reason}，必填留痕）。 */
    @PostMapping("/{id}/rollback")
    public ApiResult<Dataset> rollback(@PathVariable Long id,
                                       @RequestBody Map<String, String> body) {
        return ApiResult.success(datasetService.rollback(id, body == null ? null : body.get("reason")));
    }

    /** 质量报告 TXT 下载（仅已发布；记录交付）。 */
    @GetMapping("/{id}/report")
    public ResponseEntity<byte[]> report(@PathVariable Long id) {
        DatasetService.ReportFile f = datasetService.report(id);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment()
                                .filename(f.filename(), StandardCharsets.UTF_8).build().toString())
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(f.bytes());
    }

    /** 交付记录分页。 */
    @GetMapping("/deliveries")
    public ApiResult<PageResult<Map<String, Object>>> deliveries(@RequestParam(defaultValue = "1") int pageNum,
                                                                 @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(datasetService.deliveries(pageNum, pageSize));
    }
}
