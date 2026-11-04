package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.PageResult;
import com.wbdz.dto.ReviewConcludeDTO;
import com.wbdz.service.ReviewService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 条件复核接口。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@RestController
@RequestMapping("/api/review")
@RequiredArgsConstructor
public class ReviewController {

    private final ReviewService reviewService;

    /** 复核单分页。 */
    @GetMapping
    public ApiResult<PageResult<Map<String, Object>>> page(@RequestParam(required = false) String status,
                                                           @RequestParam(required = false) String line,
                                                           @RequestParam(required = false) Long taskId,
                                                           @RequestParam(defaultValue = "1") int pageNum,
                                                           @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(reviewService.page(status, line, taskId, pageNum, pageSize));
    }

    /** 复核单详情（含条目）。 */
    @GetMapping("/{id}")
    public ApiResult<Map<String, Object>> detail(@PathVariable Long id) {
        return ApiResult.success(reviewService.detail(id));
    }

    /** 数据集明细「加入复核任务」（无未闭环单时新建）。 */
    @PostMapping("/item/{datasetItemId}/add")
    public ApiResult<Map<String, Object>> addFromDatasetItem(@PathVariable Long datasetItemId) {
        var order = reviewService.addFromDatasetItem(datasetItemId);
        return ApiResult.success(Map.of("orderId", order.getId(), "orderBizNo", order.getBizNo()));
    }

    /** 条目结论（保存不闭环）。 */
    @PostMapping("/item/{itemId}/conclude")
    public ApiResult<Void> conclude(@PathVariable Long itemId, @RequestBody @Valid ReviewConcludeDTO dto) {
        reviewService.conclude(itemId, dto.conclusion(), dto.revisedPayload());
        return ApiResult.success();
    }

    /** 撤销条目结论（闭环前）。 */
    @PostMapping("/item/{itemId}/unconclude")
    public ApiResult<Void> unconclude(@PathVariable Long itemId) {
        reviewService.unconclude(itemId);
        return ApiResult.success();
    }

    /** 整单闭环（全部条目出结论后；回写数据集与任务状态）。 */
    @PostMapping("/{id}/close")
    public ApiResult<Void> close(@PathVariable Long id) {
        reviewService.close(id);
        return ApiResult.success();
    }
}
