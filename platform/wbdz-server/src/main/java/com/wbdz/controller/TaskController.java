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

    /** 创建任务（草稿）。 */
    @Operation(summary = "创建任务")
    @PostMapping
    public ApiResult<TaskVO> create(@RequestBody @Valid TaskCreateDTO dto) {
        return ApiResult.success(taskService.create(dto));
    }

    /** 任务分页（产线/状态/名称/优先级筛选）。 */
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

    /** 任务详情（环节执行/数据集/复核单/参数快照）。 */
    @Operation(summary = "查询任务详情")
    @GetMapping("/{id}")
    public ApiResult<TaskDetailVO> detail(@PathVariable Long id) {
        return ApiResult.success(taskService.detail(id));
    }

    /** 修改草稿任务。 */
    @Operation(summary = "编辑草稿任务")
    @PutMapping("/{id}")
    public ApiResult<TaskVO> update(@PathVariable Long id, @RequestBody @Valid TaskUpdateDTO dto) {
        return ApiResult.success(taskService.update(id, dto));
    }

    /** 提交（草稿 → 待处理）。 */
    @Operation(summary = "提交任务")
    @PostMapping("/{id}/submit")
    public ApiResult<Void> submit(@PathVariable Long id) {
        taskService.submit(id);
        return ApiResult.success();
    }

    /** 启动执行（异步编排整链）。 */
    @Operation(summary = "启动任务")
    @PostMapping("/{id}/start")
    public ApiResult<Void> start(@PathVariable Long id) {
        taskService.start(id);
        return ApiResult.success();
    }

    /** 驳回重跑（默认从第 1 环节整链重跑）。 */
    @Operation(summary = "驳回并重跑任务")
    @PostMapping("/{id}/reject")
    public ApiResult<Void> reject(@PathVariable Long id,
                                  @RequestBody(required = false) @Valid TaskRejectDTO dto) {
        Integer fromStage = dto == null ? null : dto.fromStage();
        taskService.reject(id, fromStage == null ? 1 : fromStage);
        return ApiResult.success();
    }

    /** 归集（待归集 → 已归集）。 */
    @Operation(summary = "归集任务")
    @PostMapping("/{id}/collect")
    public ApiResult<Void> collect(@PathVariable Long id) {
        taskService.collect(id);
        return ApiResult.success();
    }

    /** 调整任务级阈值（有结论后锁定）。 */
    @Operation(summary = "调整任务阈值")
    @PutMapping("/{id}/threshold")
    public ApiResult<Void> threshold(@PathVariable Long id, @RequestBody @Valid TaskThresholdDTO dto) {
        taskService.updateThreshold(id, dto.threshold());
        return ApiResult.success();
    }

    /** 删除草稿任务。 */
    @Operation(summary = "删除草稿任务")
    @DeleteMapping("/{id}")
    public ApiResult<Void> delete(@PathVariable Long id) {
        taskService.delete(id);
        return ApiResult.success();
    }
}