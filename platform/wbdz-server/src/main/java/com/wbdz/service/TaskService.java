package com.wbdz.service;

import com.wbdz.common.PageResult;
import com.wbdz.dto.TaskCreateDTO;
import com.wbdz.dto.TaskUpdateDTO;
import com.wbdz.vo.TaskDetailVO;
import com.wbdz.vo.TaskRowVO;
import com.wbdz.vo.TaskVO;

import java.math.BigDecimal;
import java.util.Map;

/**
 * 任务服务。
 *
 * @author wbdz
 * @since 2026-11-05
 */
public interface TaskService {

    /** 任务状态中文名。 */
    Map<String, String> STATUS_NAMES = Map.of(
            "draft", "草稿", "pending", "待处理", "processing", "加工中",
            "waitreview", "待复核", "quality", "待归集", "collected", "已归集", "reject", "已驳回");

    /** 创建草稿任务。 */
    TaskVO create(TaskCreateDTO dto);

    /** 修改草稿任务。 */
    TaskVO update(Long id, TaskUpdateDTO dto);

    /** 提交任务。 */
    void submit(Long id);

    /** 启动任务。 */
    void start(Long id);

    /** 驳回并从指定环节重跑。 */
    void reject(Long id, int fromStage);

    /** 归集任务。 */
    void collect(Long id);

    /** 调整任务阈值。 */
    void updateThreshold(Long id, BigDecimal threshold);

    /** 删除草稿任务。 */
    void delete(Long id);

    /** 分页查询任务。 */
    PageResult<TaskRowVO> page(String line, String status, String name, String priority,
                               int pageNum, int pageSize);

    /** 查询任务详情。 */
    TaskDetailVO detail(Long id);
}