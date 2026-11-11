package com.hsmty.tcs.controller;

import com.hsmty.core.common.entity.ApiPageResult;
import com.hsmty.core.common.entity.ApiResult;
import com.hsmty.core.common.entity.PageResult;
import com.hsmty.tcs.pojo.dto.TaskCreateDTO;
import com.hsmty.tcs.pojo.dto.TaskListDTO;
import com.hsmty.tcs.pojo.dto.TaskRejectDTO;
import com.hsmty.tcs.pojo.dto.TaskThresholdDTO;
import com.hsmty.tcs.pojo.dto.TaskUpdateDTO;
import com.hsmty.tcs.pojo.vo.TaskDetailVO;
import com.hsmty.tcs.pojo.vo.TaskRowVO;
import com.hsmty.tcs.pojo.vo.TaskVO;
import com.hsmty.tcs.service.TaskService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * <p>任务管理接口（四个产线工作台共用）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Tag(name = "任务管理", description = "任务创建、编辑、执行、驳回重跑和归集")
@RestController
@RequestMapping("task")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;

    /**
     * <p>创建任务。
     */
    @Operation(summary = "创建任务")
    @PreAuthorize("hasAnyAuthority('tcs:task:create')")
    @PostMapping
    public ApiResult<TaskVO> create(@RequestBody @Valid TaskCreateDTO dto) {
        return ApiResult.success(taskService.create(dto));
    }

    /**
     * <p>分页查询任务。
     */
    @Operation(summary = "分页查询任务")
    @PreAuthorize("hasAnyAuthority('tcs:task:page')")
    @GetMapping
    public ApiResult<PageResult<TaskRowVO>> page(TaskListDTO dto) {
        return ApiPageResult.success(taskService.page(dto));
    }

    /**
     * <p>查询任务详情。
     */
    @Operation(summary = "查询任务详情（支持 ID 或业务编号）")
    @PreAuthorize("hasAnyAuthority('tcs:task:detail')")
    @GetMapping("/{reference}")
    public ApiResult<TaskDetailVO> detail(@PathVariable String reference) {
        return ApiResult.success(taskService.detail(taskService.resolveId(reference)));
    }

    /**
     * <p>编辑草稿任务。
     */
    @Operation(summary = "编辑草稿任务")
    @PreAuthorize("hasAnyAuthority('tcs:task:update')")
    @PutMapping("/{reference}")
    public ApiResult<TaskVO> update(@PathVariable String reference,
                                    @RequestBody @Valid TaskUpdateDTO dto) {
        return ApiResult.success(taskService.update(taskService.resolveId(reference), dto));
    }

    /**
     * <p>提交任务。
     */
    @Operation(summary = "提交任务")
    @PreAuthorize("hasAnyAuthority('tcs:task:submit')")
    @PostMapping("/{reference}/submit")
    public ApiResult<Void> submit(@PathVariable String reference) {
        taskService.submit(taskService.resolveId(reference));
        return ApiResult.success();
    }

    /**
     * <p>启动任务。
     */
    @Operation(summary = "启动任务")
    @PreAuthorize("hasAnyAuthority('tcs:task:start')")
    @PostMapping("/{reference}/start")
    public ApiResult<Void> start(@PathVariable String reference) {
        taskService.start(taskService.resolveId(reference));
        return ApiResult.success();
    }

    /**
     * <p>驳回并重跑任务。
     */
    @Operation(summary = "驳回并重跑任务")
    @PreAuthorize("hasAnyAuthority('tcs:task:reject')")
    @PostMapping("/{reference}/reject")
    public ApiResult<Void> reject(@PathVariable String reference,
                                  @RequestBody(required = false) @Valid TaskRejectDTO dto) {
        Integer fromStage = dto == null ? null : dto.fromStage();
        taskService.reject(taskService.resolveId(reference), fromStage == null ? 1 : fromStage);
        return ApiResult.success();
    }

    /**
     * <p>归集任务。
     */
    @Operation(summary = "归集任务")
    @PreAuthorize("hasAnyAuthority('tcs:task:collect')")
    @PostMapping("/{reference}/collect")
    public ApiResult<Void> collect(@PathVariable String reference) {
        taskService.collect(taskService.resolveId(reference));
        return ApiResult.success();
    }

    /**
     * <p>调整任务阈值。
     */
    @Operation(summary = "调整任务阈值")
    @PreAuthorize("hasAnyAuthority('tcs:task:threshold')")
    @PutMapping("/{reference}/threshold")
    public ApiResult<Void> threshold(@PathVariable String reference,
                                     @RequestBody @Valid TaskThresholdDTO dto) {
        taskService.updateThreshold(taskService.resolveId(reference), dto.threshold());
        return ApiResult.success();
    }

    /**
     * <p>删除草稿任务（逻辑删除）。
     */
    @Operation(summary = "删除草稿任务")
    @PreAuthorize("hasAnyAuthority('tcs:task:remove')")
    @DeleteMapping("/{reference}")
    public ApiResult<Void> delete(@PathVariable String reference) {
        taskService.remove(taskService.resolveId(reference));
        return ApiResult.success();
    }
}
