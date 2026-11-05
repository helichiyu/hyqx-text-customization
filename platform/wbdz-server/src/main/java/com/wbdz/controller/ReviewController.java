package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.PageResult;
import com.wbdz.dto.ReviewConcludeDTO;
import com.wbdz.service.ReviewService;
import com.wbdz.vo.ReviewAddResultVO;
import com.wbdz.vo.ReviewDetailVO;
import com.wbdz.vo.ReviewOrderVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 条件复核接口。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Tag(name = "条件复核", description = "复核单查询、条目结论和整单闭环")
@RestController
@RequestMapping("/api/review")
@RequiredArgsConstructor
public class ReviewController {

    private final ReviewService reviewService;

    /** 复核单分页。 */
    @Operation(summary = "分页查询复核单")
    @GetMapping
    public ApiResult<PageResult<ReviewOrderVO>> page(@RequestParam(required = false) String status,
                                                     @RequestParam(required = false) String line,
                                                     @RequestParam(required = false) Long taskId,
                                                     @RequestParam(defaultValue = "1") int pageNum,
                                                     @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(reviewService.page(status, line, taskId, pageNum, pageSize));
    }

    /** 复核单详情（含条目）。 */
    @Operation(summary = "查询复核单详情")
    @GetMapping("/{id}")
    public ApiResult<ReviewDetailVO> detail(@PathVariable Long id) {
        return ApiResult.success(reviewService.detail(id));
    }

    /** 数据集明细「加入复核任务」（无未闭环单时新建）。 */
    @Operation(summary = "将数据集条目加入复核")
    @PostMapping("/item/{datasetItemId}/add")
    public ApiResult<ReviewAddResultVO> addFromDatasetItem(@PathVariable Long datasetItemId) {
        return ApiResult.success(reviewService.addFromDatasetItem(datasetItemId));
    }

    /** 条目结论（保存不闭环）。 */
    @Operation(summary = "保存复核条目结论")
    @PostMapping("/item/{itemId}/conclude")
    public ApiResult<Void> conclude(@PathVariable Long itemId, @RequestBody @Valid ReviewConcludeDTO dto) {
        reviewService.conclude(itemId, dto.conclusion(), dto.revisedPayload());
        return ApiResult.success();
    }

    /** 撤销条目结论（闭环前）。 */
    @Operation(summary = "撤销复核条目结论")
    @PostMapping("/item/{itemId}/unconclude")
    public ApiResult<Void> unconclude(@PathVariable Long itemId) {
        reviewService.unconclude(itemId);
        return ApiResult.success();
    }

    /** 整单闭环（全部条目出结论后；回写数据集与任务状态）。 */
    @Operation(summary = "复核单闭环")
    @PostMapping("/{id}/close")
    public ApiResult<Void> close(@PathVariable Long id) {
        reviewService.close(id);
        return ApiResult.success();
    }
}