package com.hsmty.tcs.service.impl;

import com.hsmty.core.common.entity.PageResult;
import com.hsmty.core.util.BeanCopyUtils;
import com.hsmty.core.util.JsonUtils;
import com.hsmty.core.util.PageUtils;
import com.hsmty.tcs.common.AuthContext;
import com.hsmty.tcs.common.BizException;
import com.hsmty.tcs.common.BizId;
import com.hsmty.tcs.common.Times;
import com.hsmty.tcs.mapper.DatasetMapper;
import com.hsmty.tcs.mapper.MatBatchMapper;
import com.hsmty.tcs.mapper.ParamVersionMapper;
import com.hsmty.tcs.mapper.ReviewItemMapper;
import com.hsmty.tcs.mapper.ReviewOrderMapper;
import com.hsmty.tcs.mapper.TaskMainMapper;
import com.hsmty.tcs.mapper.TaskStageRunMapper;
import com.hsmty.tcs.operator.LineRegistry;
import com.hsmty.tcs.operator.OperatorFileService;
import com.hsmty.tcs.operator.TaskOrchestrator;
import com.hsmty.tcs.pojo.dto.TaskCreateDTO;
import com.hsmty.tcs.pojo.dto.TaskListDTO;
import com.hsmty.tcs.pojo.dto.TaskUpdateDTO;
import com.hsmty.tcs.pojo.po.DatasetEntity;
import com.hsmty.tcs.pojo.po.MatBatchEntity;
import com.hsmty.tcs.pojo.po.ParamVersionEntity;
import com.hsmty.tcs.pojo.po.ReviewOrderEntity;
import com.hsmty.tcs.pojo.po.TaskMainEntity;
import com.hsmty.tcs.pojo.po.TaskStageRunEntity;
import com.hsmty.tcs.pojo.vo.TaskDetailVO;
import com.hsmty.tcs.pojo.vo.TaskRowVO;
import com.hsmty.tcs.pojo.vo.TaskVO;
import com.hsmty.tcs.service.ParamService;
import com.hsmty.tcs.service.TaskService;
import com.mybatisflex.core.paginate.Page;
import com.mybatisflex.core.query.QueryWrapper;
import com.mybatisflex.spring.service.impl.ServiceImpl;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.type.TypeReference;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * <p>任务管理：创建（锁定参数快照）→ 提交 → 启动编排 → 复核/归集 → 驳回重跑。
 *
 * <p>状态机：draft → pending → processing → (waitreview | quality) → collected；
 * 驳回（waitreview/quality）→ reject → processing（从指定环节重跑）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Service
@RequiredArgsConstructor
public class TaskServiceImpl extends ServiceImpl<TaskMainMapper, TaskMainEntity> implements TaskService {

    private static final List<String> PRIORITIES = List.of("high", "mid", "low");

    private static final TypeReference<List<Map<String, Object>>> MAP_LIST =
            new TypeReference<List<Map<String, Object>>>() {
            };

    private final TaskMainMapper taskMapper;

    private final MatBatchMapper batchMapper;

    private final TaskStageRunMapper stageRunMapper;

    private final ReviewOrderMapper reviewOrderMapper;

    private final ReviewItemMapper reviewItemMapper;

    private final ParamVersionMapper paramVersionMapper;

    private final DatasetMapper datasetMapper;

    private final ParamService paramService;

    private final TaskOrchestrator orchestrator;

    private final OperatorFileService fileService;

    // ==================== 动作 ====================

    /**
     * 创建任务（草稿；锁定参数版本快照）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public TaskVO create(TaskCreateDTO dto) {
        require(LineRegistry.LINE_NAMES.containsKey(dto.line()), "产线不存在");
        if (dto.priority() != null && !dto.priority().isBlank()
                && !PRIORITIES.contains(dto.priority())) {
            throw new BizException("优先级取值：high/mid/low");
        }
        if ("graphic".equals(dto.line())) {
            require(dto.imageClass() != null && LineRegistry.IMAGE_CLASSES.contains(dto.imageClass()),
                    "图文融合任务必须选择大类：" + String.join("/", LineRegistry.IMAGE_CLASSES));
        }
        MatBatchEntity batch = batchMapper.selectOneById(dto.batchId());
        require(batch != null, "素材批次不存在");
        require(batch.getLine().equals(dto.line()), "素材批次与任务产线不一致");
        require("released".equals(batch.getStatus()), "素材批次未移交，不能创建任务");

        ParamVersionEntity param = resolveParam(dto.line(), dto.paramVersion());
        TaskMainEntity task = new TaskMainEntity();
        task.setBizNo(BizId.nextUnique("TASK", candidate -> taskMapper.selectCountByQuery(
                QueryWrapper.create().where("biz_no = ?", candidate)) > 0));
        task.setName(dto.name().trim());
        task.setLine(dto.line());
        task.setStatus("draft");
        task.setPriority(dto.priority() == null || dto.priority().isBlank() ? "mid" : dto.priority());
        task.setImageClass(dto.imageClass());
        task.setBatchId(dto.batchId());
        task.setParamVersion(param.getVersion());
        task.setParamSnapshot(param.getContent());
        task.setThreshold(dto.threshold() == null ? new BigDecimal("0.80") : dto.threshold());
        task.setCurrentStage(0);
        task.setCreateBy(AuthContext.username());
        taskMapper.insert(task);
        return toVO(task);
    }

    /**
     * 修改草稿任务；重新校验批次、参数版本和图文大类。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public TaskVO update(Long id, TaskUpdateDTO dto) {
        TaskMainEntity task = load(id);
        require("draft".equals(task.getStatus()), "仅草稿任务可编辑");
        if (dto.priority() != null && !dto.priority().isBlank()
                && !PRIORITIES.contains(dto.priority())) {
            throw new BizException("优先级取值：high/mid/low");
        }
        if ("graphic".equals(task.getLine())) {
            require(dto.imageClass() != null && LineRegistry.IMAGE_CLASSES.contains(dto.imageClass()),
                    "图文融合任务必须选择大类：" + String.join("/", LineRegistry.IMAGE_CLASSES));
        }
        MatBatchEntity batch = batchMapper.selectOneById(dto.batchId());
        require(batch != null, "素材批次不存在");
        require(batch.getLine().equals(task.getLine()), "素材批次与任务产线不一致");
        require("released".equals(batch.getStatus()), "素材批次未移交，不能保存任务");

        ParamVersionEntity param = resolveParam(task.getLine(), dto.paramVersion());
        task.setName(dto.name().trim());
        task.setPriority(dto.priority() == null || dto.priority().isBlank() ? "mid" : dto.priority());
        task.setImageClass("graphic".equals(task.getLine()) ? dto.imageClass() : null);
        task.setBatchId(dto.batchId());
        task.setParamVersion(param.getVersion());
        task.setParamSnapshot(param.getContent());
        if (dto.threshold() != null) {
            task.setThreshold(dto.threshold());
        }
        taskMapper.update(task);
        return toVO(task);
    }

    /**
     * 提交（草稿 → 待处理）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void submit(Long id) {
        TaskMainEntity task = load(id);
        require("draft".equals(task.getStatus()), "仅草稿可提交");
        task.setStatus("pending");
        taskMapper.update(task);
    }

    /**
     * 启动执行（待处理 → 加工中，异步编排整链）。
     */
    @Override
    public void start(Long id) {
        TaskMainEntity task = load(id);
        require("pending".equals(task.getStatus()), "仅待处理任务可启动");
        MatBatchEntity batch = batchMapper.selectOneById(task.getBatchId());
        require(batch != null && "released".equals(batch.getStatus()), "素材批次未移交，不能启动任务");
        orchestrator.startAsync(id, 1);
    }

    /**
     * 驳回重跑（待复核/待归集 → 已驳回 → 加工中，从指定环节续链）。
     */
    @Override
    public void reject(Long id, int fromStage) {
        TaskMainEntity task = load(id);
        require("waitreview".equals(task.getStatus()) || "quality".equals(task.getStatus()),
                "仅待复核/待归集任务可驳回重跑");
        require(fromStage >= 1 && fromStage <= 3, "环节号取值 1-3");
        task.setStatus("reject");
        taskMapper.update(task);
        orchestrator.startAsync(id, fromStage);
    }

    /**
     * 归集（待归集 → 已归集；数据集已在链路完成时生成）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void collect(Long id) {
        TaskMainEntity task = load(id);
        require("quality".equals(task.getStatus()), "仅待归集任务可归集");
        task.setStatus("collected");
        taskMapper.update(task);
    }

    /**
     * 调整任务级阈值（任一复核条目出结论后锁定）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateThreshold(Long id, BigDecimal threshold) {
        TaskMainEntity task = load(id);
        require(threshold != null && threshold.compareTo(BigDecimal.ZERO) > 0
                && threshold.compareTo(BigDecimal.ONE) <= 0, "阈值取值 (0,1]");
        Long concluded = reviewItemConcludedCount(id);
        require(concluded == null || concluded == 0, "已有复核条目出结论，阈值已锁定");
        task.setThreshold(threshold);
        taskMapper.update(task);
    }

    /**
     * 删除（仅草稿，逻辑删除）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void remove(Long id) {
        TaskMainEntity task = load(id);
        require("draft".equals(task.getStatus()), "仅草稿任务可删除");
        taskMapper.deleteById(id);
    }

    @Override
    public Long resolveId(String reference) {
        String ref = reference == null ? "" : reference.trim();
        if (ref.matches("\\d+")) {
            try {
                return Long.valueOf(ref);
            } catch (NumberFormatException e) {
                throw new BizException("任务引用格式错误", e);
            }
        }
        TaskMainEntity task = taskMapper.selectOneByQuery(QueryWrapper.create()
                .where("biz_no = ?", ref));
        if (task == null) {
            throw new BizException("任务不存在");
        }
        return task.getId();
    }

    // ==================== 查询 ====================

    @Override
    public PageResult<TaskRowVO> page(TaskListDTO dto) {
        QueryWrapper qw = QueryWrapper.create();
        if (dto.getLine() != null && !dto.getLine().isBlank()) {
            qw.and("line = ?", dto.getLine());
        }
        if (dto.getStatus() != null && !dto.getStatus().isBlank()) {
            qw.and("status = ?", dto.getStatus());
        }
        if (dto.getName() != null && !dto.getName().isBlank()) {
            qw.and("name like ?", "%" + dto.getName().trim() + "%");
        }
        if (dto.getPriority() != null && !dto.getPriority().isBlank()) {
            qw.and("priority = ?", dto.getPriority());
        }
        qw.orderBy("priority asc", "create_time desc");
        Page<TaskMainEntity> page = taskMapper.paginate(PageUtils.getPage(dto), qw);
        return PageUtils.getPageResult(page.map(this::toRowVO));
    }

    /**
     * 任务详情：任务 + 环节执行 + 数据集 + 复核单 + 参数快照。
     */
    @Override
    public TaskDetailVO detail(Long id) {
        TaskMainEntity task = load(id);
        TaskDetailVO detail = BeanCopyUtils.copy(toVO(task), TaskDetailVO.class);
        detail.setStageNames(LineRegistry.STAGE_NAMES.get(task.getLine()));
        detail.setParamSnapshot(task.getParamSnapshot() == null || task.getParamSnapshot().isBlank()
                ? List.of() : JsonUtils.parseArray(task.getParamSnapshot(), MAP_LIST));
        detail.setRunning(orchestrator.isRunning(id));

        MatBatchEntity batch = task.getBatchId() == null ? null : batchMapper.selectOneById(task.getBatchId());
        if (batch != null) {
            TaskDetailVO.Batch batchView = new TaskDetailVO.Batch();
            batchView.setId(batch.getId());
            batchView.setBizNo(batch.getBizNo());
            batchView.setName(batch.getName());
            batchView.setFileCount(batch.getFileCount() == null ? 0 : batch.getFileCount());
            detail.setBatch(batchView);
        }

        List<TaskDetailVO.StageRun> runs = new ArrayList<>();
        for (TaskStageRunEntity runRow : stageRunMapper.selectListByQuery(QueryWrapper.create()
                .where("task_id = ?", id).orderBy("id asc"))) {
            TaskDetailVO.StageRun run = new TaskDetailVO.StageRun();
            run.setId(runRow.getId());
            run.setStageNo(runRow.getStageNo());
            run.setStageName(runRow.getStageName());
            run.setOperatorTag(runRow.getOperatorTag());
            run.setStatus(runRow.getStatus());
            run.setAttempt(runRow.getAttempt());
            run.setSummary(runRow.getSummary() == null || runRow.getSummary().isBlank()
                    ? null : JsonUtils.jsonToMap(runRow.getSummary()));
            run.setSkipped(runRow.getSkipped() == null || runRow.getSkipped().isBlank()
                    ? List.of() : JsonUtils.parseArray(runRow.getSkipped(), MAP_LIST));
            run.setFailed(runRow.getFailed() == null || runRow.getFailed().isBlank()
                    ? List.of() : JsonUtils.parseArray(runRow.getFailed(), MAP_LIST));
            run.setStartTime(Times.text(runRow.getStartTime()));
            run.setEndTime(Times.text(runRow.getEndTime()));
            run.setProgress(fileService.progress(runRow.getOperatorTag(), runRow.getId()));
            runs.add(run);
        }
        detail.setStageRuns(runs);

        detail.setDatasets(datasetMapper.selectListByQuery(QueryWrapper.create()
                        .where("task_id = ?", id).orderBy("id desc")).stream()
                .map(this::datasetBrief).toList());

        detail.setReviewOrders(reviewOrderMapper.selectListByQuery(QueryWrapper.create()
                        .where("task_id = ?", id).orderBy("id desc")).stream()
                .map(order -> {
                    TaskDetailVO.ReviewOrderBrief brief = new TaskDetailVO.ReviewOrderBrief();
                    brief.setId(order.getId());
                    brief.setBizNo(order.getBizNo());
                    brief.setStatus(order.getStatus());
                    brief.setStageName(order.getStageName());
                    brief.setItemCount(order.getItemCount());
                    brief.setTriggerDesc(order.getTriggerDesc());
                    return brief;
                }).toList());
        return detail;
    }

    private TaskDetailVO.DatasetBrief datasetBrief(DatasetEntity dataset) {
        TaskDetailVO.DatasetBrief brief = new TaskDetailVO.DatasetBrief();
        brief.setId(dataset.getId());
        brief.setBizNo(dataset.getBizNo());
        brief.setSemVer(dataset.getSemVer());
        brief.setStatus(dataset.getStatus());
        brief.setItemCount(dataset.getItemCount());
        brief.setSkipCount(dataset.getSkipCount());
        brief.setCreateTime(Times.text(dataset.getCreateTime()));
        return brief;
    }

    // ==================== 内部 ====================

    private TaskMainEntity load(Long id) {
        TaskMainEntity task = taskMapper.selectOneById(id);
        if (task == null) {
            throw new BizException("任务不存在");
        }
        return task;
    }

    private ParamVersionEntity resolveParam(String line, String version) {
        ParamVersionEntity v = version == null || version.isBlank()
                ? paramService.latest(line)
                : paramVersionMapper.selectOneByQuery(QueryWrapper.create()
                        .where("line = ?", line)
                        .and("version = ?", version));
        if (v == null) {
            throw new BizException("该产线尚无已发布参数版本，请先在参数配置中发布");
        }
        return v;
    }

    /**
     * 任务下已出结论的复核条目数（阈值锁定判定）。
     */
    private Long reviewItemConcludedCount(Long taskId) {
        return reviewItemMapper.selectCountByQuery(QueryWrapper.create()
                .where("task_id = ?", taskId)
                .and("conclusion is not null"));
    }

    private TaskVO toVO(TaskMainEntity task) {
        TaskVO vo = BeanCopyUtils.copy(task, TaskVO.class);
        vo.setLineName(LineRegistry.LINE_NAMES.get(task.getLine()));
        vo.setStatusName(STATUS_NAMES.get(task.getStatus()));
        vo.setCreateTime(Times.text(task.getCreateTime()));
        return vo;
    }

    private TaskRowVO toRowVO(TaskMainEntity task) {
        TaskRowVO row = BeanCopyUtils.copy(toVO(task), TaskRowVO.class);
        MatBatchEntity b = task.getBatchId() == null ? null : batchMapper.selectOneById(task.getBatchId());
        row.setBatchBizNo(b == null ? null : b.getBizNo());
        row.setBatchName(b == null ? null : b.getName());
        row.setDatasetCount(datasetMapper.selectCountByQuery(QueryWrapper.create()
                .where("task_id = ?", task.getId())));
        return row;
    }

    private void require(boolean cond, String msg) {
        if (!cond) {
            throw new BizException(msg);
        }
    }
}
