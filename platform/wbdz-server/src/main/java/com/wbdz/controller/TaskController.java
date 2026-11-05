package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.PageResult;
import com.wbdz.dto.TaskCreateDTO;
import com.wbdz.dto.TaskRejectDTO;
import com.wbdz.dto.TaskThresholdDTO;
import com.wbdz.dto.TaskUpdateDTO;
import com.wbdz.service.TaskService;
import com.wbdz.vo.TaskDetailVO;
import com.wbdz.vo.TaskRowVO;
import com.wbdz.vo.TaskVO;
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

/**
 * 任务管理接口（四个产线工作台共用）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Tag(name = "任务管理", description = "任务创建、编辑、执行、驳回重跑和归集")
@RestController
@RequestMapping("/api/task")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;

    @Operation(summary = "创建任务")
    @PostMapping
    public ApiResult<TaskVO> create(@RequestBody @Valid TaskCreateDTO dto) {
        return ApiResult.success(taskService.create(dto));
    }

    @Operation(summary = "分页查询任务")
    @GetMapping
    public ApiResult<PageResult<TaskRowVO>> page(@RequestParam(required = false) String line,
                                                 @RequestParam(required = false) String status,
                                                 @RequestParam(required = false) String name,
                                                 @RequestParam(required = false) String priority,
                                                 @RequestParam(defaultValue = "1") int pageNum,
                                                 @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(taskService.page(line, status, name, priority, pageNum, pageSize));
    }

    @Operation(summary = "按业务编号查询任务详情")
    @GetMapping("/by-no/{bizNo}")
    public ApiResult<TaskDetailVO> detailByBizNo(@PathVariable String bizNo) {
        return detail(bizNo);
    }

    @Operation(summary = "查询任务详情")
    @GetMapping("/{reference}")
    public ApiResult<TaskDetailVO> detail(@PathVariable String reference) {
        return ApiResult.success(taskService.detail(taskService.resolveId(reference)));
    }

    @Operation(summary = "编辑草稿任务")
    @PutMapping("/{reference}")
    public ApiResult<TaskVO> update(@PathVariable String reference, @RequestBody @Valid TaskUpdateDTO dto) {
        return ApiResult.success(taskService.update(taskService.resolveId(reference), dto));
    }

    @Operation(summary = "提交任务")
    @PostMapping("/{reference}/submit")
    public ApiResult<Void> submit(@PathVariable String reference) {
        taskService.submit(taskService.resolveId(reference));
        return ApiResult.success();
    }

    @Operation(summary = "启动任务")
    @PostMapping("/{reference}/start")
    public ApiResult<Void> start(@PathVariable String reference) {
        taskService.start(taskService.resolveId(reference));
        return ApiResult.success();
    }

    @Operation(summary = "驳回并重跑任务")
    @PostMapping("/{reference}/reject")
    public ApiResult<Void> reject(@PathVariable String reference,
                                  @RequestBody(required = false) @Valid TaskRejectDTO dto) {
        Integer fromStage = dto == null ? null : dto.fromStage();
        taskService.reject(taskService.resolveId(reference), fromStage == null ? 1 : fromStage);
        return ApiResult.success();
    }

    @Operation(summary = "归集任务")
    @PostMapping("/{reference}/collect")
    public ApiResult<Void> collect(@PathVariable String reference) {
        taskService.collect(taskService.resolveId(reference));
        return ApiResult.success();
    }

    @Operation(summary = "调整任务阈值")
    @PutMapping("/{reference}/threshold")
    public ApiResult<Void> threshold(@PathVariable String reference, @RequestBody @Valid TaskThresholdDTO dto) {
        taskService.updateThreshold(taskService.resolveId(reference), dto.threshold());
        return ApiResult.success();
    }

    @Operation(summary = "删除草稿任务")
    @DeleteMapping("/{reference}")
    public ApiResult<Void> delete(@PathVariable String reference) {
        taskService.delete(taskService.resolveId(reference));
        return ApiResult.success();
    }
}