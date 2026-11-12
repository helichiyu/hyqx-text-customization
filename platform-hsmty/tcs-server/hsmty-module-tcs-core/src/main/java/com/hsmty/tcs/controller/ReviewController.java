package com.hsmty.tcs.controller;

import com.hsmty.core.common.entity.ApiPageResult;
import com.hsmty.core.common.entity.ApiResult;
import com.hsmty.core.common.entity.PageResult;
import com.hsmty.tcs.pojo.dto.ReviewConcludeDTO;
import com.hsmty.tcs.pojo.dto.ReviewListDTO;
import com.hsmty.tcs.pojo.vo.ReviewAddResultVO;
import com.hsmty.tcs.pojo.vo.ReviewDetailVO;
import com.hsmty.tcs.pojo.vo.ReviewOrderVO;
import com.hsmty.tcs.service.ReviewService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * <p>条件复核接口。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Tag(name = "条件复核", description = "复核单查询、条目结论和整单闭环")
@RestController
@RequestMapping("review")
@RequiredArgsConstructor
public class ReviewController {

    private final ReviewService reviewService;

    /**
     * <p>分页查询复核单。
     */
    @Operation(summary = "分页查询复核单")
    @PreAuthorize("hasAnyAuthority('tcs:review:page')")
    @GetMapping
    public ApiResult<PageResult<ReviewOrderVO>> page(ReviewListDTO dto) {
        return ApiPageResult.success(reviewService.page(dto));
    }

    /**
     * <p>查询复核单详情。
     */
    @Operation(summary = "查询复核单详情（支持 ID 或业务编号）")
    @PreAuthorize("hasAnyAuthority('tcs:review:detail')")
    @GetMapping("/{reference}")
    public ApiResult<ReviewDetailVO> detail(@PathVariable String reference) {
        return ApiResult.success(reviewService.detail(reviewService.resolveId(reference)));
    }

    /**
     * <p>将数据集条目加入复核。
     */
    @Operation(summary = "将数据集条目加入复核")
    @PreAuthorize("hasAnyAuthority('tcs:review:add')")
    @PostMapping("/item/{datasetItemId}/add")
    public ApiResult<ReviewAddResultVO> addFromDatasetItem(@PathVariable Long datasetItemId) {
        return ApiResult.success(reviewService.addFromDatasetItem(datasetItemId));
    }

    /**
     * <p>保存复核条目结论。
     */
    @Operation(summary = "保存复核条目结论")
    @PreAuthorize("hasAnyAuthority('tcs:review:conclude')")
    @PostMapping("/item/{itemId}/conclude")
    public ApiResult<Void> conclude(@PathVariable Long itemId,
                                    @RequestBody @Valid ReviewConcludeDTO dto) {
        reviewService.conclude(itemId, dto.conclusion(), dto.revisedPayload());
        return ApiResult.success();
    }

    /**
     * <p>撤销复核条目结论。
     */
    @Operation(summary = "撤销复核条目结论")
    @PreAuthorize("hasAnyAuthority('tcs:review:conclude')")
    @PostMapping("/item/{itemId}/unconclude")
    public ApiResult<Void> unconclude(@PathVariable Long itemId) {
        reviewService.unconclude(itemId);
        return ApiResult.success();
    }

    /**
     * <p>复核单闭环。
     */
    @Operation(summary = "复核单闭环")
    @PreAuthorize("hasAnyAuthority('tcs:review:close')")
    @PostMapping("/{reference}/close")
    public ApiResult<Void> close(@PathVariable String reference) {
        reviewService.close(reviewService.resolveId(reference));
        return ApiResult.success();
    }

    /**
     * <p>删除复核单（逻辑删除，级联删除条目）。
     */
    @Operation(summary = "删除复核单")
    @PreAuthorize("hasAnyAuthority('tcs:review:remove')")
    @DeleteMapping("/{reference}")
    public ApiResult<Void> delete(@PathVariable String reference) {
        reviewService.remove(reviewService.resolveId(reference));
        return ApiResult.success();
    }
}
