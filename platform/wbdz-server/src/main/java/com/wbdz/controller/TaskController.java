package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.PageResult;
import com.wbdz.dto.TaskCreateDTO;
import com.wbdz.entity.TaskMain;
import com.wbdz.service.TaskService;
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

import java.math.BigDecimal;
import java.util.Map;

/**
 * 任务管理接口（四个产线工作台共用）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@RestController
@RequestMapping("/api/task")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;

    /** 创建任务（草稿）。 */
    @PostMapping
    public ApiResult<TaskMain> create(@RequestBody @Valid TaskCreateDTO dto) {
        return ApiResult.success(taskService.create(dto));
    }

    /** 任务分页（产线/状态/名称/优先级筛选）。 */
    @GetMapping
    public ApiResult<PageResult<Map<String, Object>>> page(@RequestParam(required = false) String line,
                                                           @RequestParam(required = false) String status,
                                                           @RequestParam(required = false) String name,
                                                           @RequestParam(required = false) String priority,
                                                           @RequestParam(defaultValue = "1") int pageNum,
                                                           @RequestParam(defaultValue = "10") int pageSize) {
        return ApiResult.success(taskService.page(line, status, name, priority, pageNum, pageSize));
    }

    /** 任务详情（环节执行/数据集/复核单/参数快照）。 */
    @GetMapping("/{id}")
    public ApiResult<Map<String, Object>> detail(@PathVariable Long id) {
        return ApiResult.success(taskService.detail(id));
    }

    /** 提交（草稿 → 待处理）。 */
    @PostMapping("/{id}/submit")
    public ApiResult<Void> submit(@PathVariable Long id) {
        taskService.submit(id);
        return ApiResult.success();
    }

    /** 启动执行（异步编排整链）。 */
    @PostMapping("/{id}/start")
    public ApiResult<Void> start(@PathVariable Long id) {
        taskService.start(id);
        return ApiResult.success();
    }

    /** 驳回重跑（body: {fromStage}，1-3，默认 1 整链重跑）。 */
    @PostMapping("/{id}/reject")
    public ApiResult<Void> reject(@PathVariable Long id,
                                  @RequestBody(required = false) Map<String, Integer> body) {
        Integer fromStage = body == null ? null : body.get("fromStage");
        taskService.reject(id, fromStage == null ? 1 : fromStage);
        return ApiResult.success();
    }

    /** 归集（待归集 → 已归集）。 */
    @PostMapping("/{id}/collect")
    public ApiResult<Void> collect(@PathVariable Long id) {
        taskService.collect(id);
        return ApiResult.success();
    }

    /** 调整任务级阈值（有结论后锁定）。 */
    @PutMapping("/{id}/threshold")
    public ApiResult<Void> threshold(@PathVariable Long id,
                                     @RequestBody Map<String, BigDecimal> body) {
        taskService.updateThreshold(id, body == null ? null : body.get("threshold"));
        return ApiResult.success();
    }

    /** 删除草稿任务。 */
    @DeleteMapping("/{id}")
    public ApiResult<Void> delete(@PathVariable Long id) {
        taskService.delete(id);
        return ApiResult.success();
    }
}
