package com.hsmty.tcs.service;

import com.hsmty.core.common.entity.PageResult;
import com.hsmty.tcs.pojo.dto.TaskCreateDTO;
import com.hsmty.tcs.pojo.dto.TaskListDTO;
import com.hsmty.tcs.pojo.dto.TaskUpdateDTO;
import com.hsmty.tcs.pojo.po.TaskMainEntity;
import com.hsmty.tcs.pojo.vo.TaskDetailVO;
import com.hsmty.tcs.pojo.vo.TaskRowVO;
import com.hsmty.tcs.pojo.vo.TaskVO;
import com.mybatisflex.core.service.IService;

import java.math.BigDecimal;
import java.util.Map;

/**
 * <p>任务服务。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public interface TaskService extends IService<TaskMainEntity> {

    /**
     * 任务状态中文名。
     */
    Map<String, String> STATUS_NAMES = Map.of(
            "draft", "草稿", "pending", "待处理", "processing", "加工中",
            "waitreview", "待复核", "quality", "待归集", "collected", "已归集", "reject", "已驳回");

    /**
     * <p>将 Long ID 或 bizNo 解析为内部主键。
     *
     * @param reference 内部主键或业务编号
     * @return 内部主键
     */
    Long resolveId(String reference);

    /**
     * <p>创建草稿任务。
     *
     * @param dto 创建入参
     * @return 任务
     */
    TaskVO create(TaskCreateDTO dto);

    /**
     * <p>修改草稿任务。
     *
     * @param id  任务内部主键
     * @param dto 修改入参
     * @return 任务
     */
    TaskVO update(Long id, TaskUpdateDTO dto);

    /**
     * <p>提交任务。
     *
     * @param id 任务内部主键
     */
    void submit(Long id);

    /**
     * <p>启动任务。
     *
     * @param id 任务内部主键
     */
    void start(Long id);

    /**
     * <p>驳回并从指定环节重跑。
     *
     * @param id        任务内部主键
     * @param fromStage 起始环节 1-3
     */
    void reject(Long id, int fromStage);

    /**
     * <p>归集任务。
     *
     * @param id 任务内部主键
     */
    void collect(Long id);

    /**
     * <p>调整任务阈值。
     *
     * @param id        任务内部主键
     * @param threshold 新阈值
     */
    void updateThreshold(Long id, BigDecimal threshold);

    /**
     * <p>删除草稿任务。
     *
     * @param id 任务内部主键
     */
    void remove(Long id);

    /**
     * <p>分页查询任务。
     *
     * @param dto 查询入参
     * @return 分页结果
     */
    PageResult<TaskRowVO> page(TaskListDTO dto);

    /**
     * <p>查询任务详情。
     *
     * @param id 任务内部主键
     * @return 任务详情
     */
    TaskDetailVO detail(Long id);
}
