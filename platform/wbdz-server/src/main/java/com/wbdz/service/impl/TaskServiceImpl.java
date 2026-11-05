package com.wbdz.service.impl;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.service.TaskService;
import com.wbdz.service.TaskOrchestrator;
import com.wbdz.service.ParamService;
import com.wbdz.service.OperatorClient;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.AuthContext;
import com.wbdz.service.TaskService;
import com.wbdz.service.TaskOrchestrator;
import com.wbdz.service.ParamService;
import com.wbdz.service.OperatorClient;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.BizException;
import com.wbdz.service.TaskService;
import com.wbdz.service.TaskOrchestrator;
import com.wbdz.service.ParamService;
import com.wbdz.service.OperatorClient;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.BizId;
import com.wbdz.service.TaskService;
import com.wbdz.service.TaskOrchestrator;
import com.wbdz.service.ParamService;
import com.wbdz.service.OperatorClient;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.PageResult;
import com.wbdz.dto.TaskCreateDTO;
import com.wbdz.dto.TaskUpdateDTO;
import com.wbdz.entity.Dataset;
import com.wbdz.entity.MatBatch;
import com.wbdz.entity.ParamVersion;
import com.wbdz.entity.ReviewOrder;
import com.wbdz.entity.TaskMain;
import com.wbdz.entity.TaskStageRun;
import com.wbdz.mapper.DatasetMapper;
import com.wbdz.mapper.MatBatchMapper;
import com.wbdz.mapper.ReviewOrderMapper;
import com.wbdz.mapper.TaskMainMapper;
import com.wbdz.mapper.TaskStageRunMapper;
import com.wbdz.vo.TaskDetailVO;
import com.wbdz.vo.TaskRowVO;
import com.wbdz.vo.TaskVO;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static com.wbdz.entity.table.DatasetTableDef.DATASET;
import static com.wbdz.entity.table.MatBatchTableDef.MAT_BATCH;
import static com.wbdz.entity.table.ParamVersionTableDef.PARAM_VERSION;
import static com.wbdz.entity.table.ReviewItemTableDef.REVIEW_ITEM;
import static com.wbdz.entity.table.ReviewOrderTableDef.REVIEW_ORDER;
import static com.wbdz.entity.table.TaskMainTableDef.TASK_MAIN;
import static com.wbdz.entity.table.TaskStageRunTableDef.TASK_STAGE_RUN;

/**
 * 任务管理：创建（锁定参数快照）→ 提交 → 启动编排 → 复核/归集 → 驳回重跑。
 *
 * <p>状态机：draft → pending → processing → (waitreview | quality) → collected；
 * 驳回（waitreview/quality）→ reject → processing（从指定环节重跑）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Service
@RequiredArgsConstructor
public class TaskServiceImpl implements TaskService {


    private static final List<String> PRIORITIES = List.of("high", "mid", "low");

    private final TaskMainMapper taskMapper;

    private final MatBatchMapper batchMapper;

    private final TaskStageRunMapper stageRunMapper;

    private final ReviewOrderMapper reviewOrderMapper;

    private final com.wbdz.mapper.ReviewItemMapper reviewItemMapper;

    private final com.wbdz.mapper.ParamVersionMapper paramVersionMapper;

    private final DatasetMapper datasetMapper;

    private final ParamService paramService;

    private final TaskOrchestrator orchestrator;

    private final OperatorClient operatorClient;

    // ==================== 动作 ====================

    /** 创建任务（草稿；锁定参数版本快照）。 */
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
        MatBatch batch = batchMapper.selectOneById(dto.batchId());
        require(batch != null, "素材批次不存在");
        require(batch.getLine().equals(dto.line()), "素材批次与任务产线不一致");
        require("released".equals(batch.getStatus()), "素材批次未移交，不能创建任务");

        ParamVersion param = resolveParam(dto.line(), dto.paramVersion());
        TaskMain task = new TaskMain();
        task.setBizNo(BizId.nextUnique("TASK", candidate -> taskMapper.selectCountByQuery(
                QueryWrapper.create().where(TASK_MAIN.BIZ_NO.eq(candidate))) > 0));
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

    /** 修改草稿任务；重新校验批次、参数版本和图文大类。 */
    @Transactional(rollbackFor = Exception.class)
    public TaskVO update(Long id, TaskUpdateDTO dto) {
        TaskMain task = load(id);
        require("draft".equals(task.getStatus()), "仅草稿任务可编辑");
        if (dto.priority() != null && !dto.priority().isBlank()
                && !PRIORITIES.contains(dto.priority())) {
            throw new BizException("优先级取值：high/mid/low");
        }
        if ("graphic".equals(task.getLine())) {
            require(dto.imageClass() != null && LineRegistry.IMAGE_CLASSES.contains(dto.imageClass()),
                    "图文融合任务必须选择大类：" + String.join("/", LineRegistry.IMAGE_CLASSES));
        }
        MatBatch batch = batchMapper.selectOneById(dto.batchId());
        require(batch != null, "素材批次不存在");
        require(batch.getLine().equals(task.getLine()), "素材批次与任务产线不一致");
        require("released".equals(batch.getStatus()), "素材批次未移交，不能保存任务");

        ParamVersion param = resolveParam(task.getLine(), dto.paramVersion());
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

    /** 提交（草稿 → 待处理）。 */
    @Transactional(rollbackFor = Exception.class)
    public void submit(Long id) {
        TaskMain task = load(id);
        require("draft".equals(task.getStatus()), "仅草稿可提交");
        task.setStatus("pending");
        taskMapper.update(task);
    }

    /** 启动执行（待处理 → 加工中，异步编排整链）。 */
    public void start(Long id) {
        TaskMain task = load(id);
        require("pending".equals(task.getStatus()), "仅待处理任务可启动");
        MatBatch batch = batchMapper.selectOneById(task.getBatchId());
        require(batch != null && "released".equals(batch.getStatus()), "素材批次未移交，不能启动任务");
        orchestrator.startAsync(id, 1);
    }

    /** 驳回重跑（待复核/待归集 → 已驳回 → 加工中，从指定环节续链）。 */
    public void reject(Long id, int fromStage) {
        TaskMain task = load(id);
        require("waitreview".equals(task.getStatus()) || "quality".equals(task.getStatus()),
                "仅待复核/待归集任务可驳回重跑");
        require(fromStage >= 1 && fromStage <= 3, "环节号取值 1-3");
        task.setStatus("reject");
        taskMapper.update(task);
        orchestrator.startAsync(id, fromStage);
    }

    /** 归集（待归集 → 已归集；数据集已在链路完成时生成）。 */
    @Transactional(rollbackFor = Exception.class)
    public void collect(Long id) {
        TaskMain task = load(id);
        require("quality".equals(task.getStatus()), "仅待归集任务可归集");
        task.setStatus("collected");
        taskMapper.update(task);
    }

    /** 调整任务级阈值（任一复核条目出结论后锁定）。 */
    @Transactional(rollbackFor = Exception.class)
    public void updateThreshold(Long id, BigDecimal threshold) {
        TaskMain task = load(id);
        require(threshold != null && threshold.compareTo(BigDecimal.ZERO) > 0
                && threshold.compareTo(BigDecimal.ONE) <= 0, "阈值取值 (0,1]");
        Long concluded = reviewItemConcludedCount(id);
        require(concluded == 0, "已有复核条目出结论，阈值已锁定");
        task.setThreshold(threshold);
        taskMapper.update(task);
    }

    /** 删除（仅草稿）。 */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        TaskMain task = load(id);
        require("draft".equals(task.getStatus()), "仅草稿任务可删除");
        taskMapper.deleteById(id);
    }

    public Long resolveId(String reference) {
        String ref = reference == null ? "" : reference.trim();
        if (ref.matches("\\d+")) {
            try {
                return Long.valueOf(ref);
            } catch (NumberFormatException e) {
                throw new BizException("任务引用格式错误", e);
            }
        }
        TaskMain task = taskMapper.selectOneByQuery(QueryWrapper.create()
                .where(TASK_MAIN.BIZ_NO.eq(ref)));
        if (task == null) {
            throw new BizException("任务不存在");
        }
        return task.getId();
    }
    // ==================== 查询 ====================

    public PageResult<TaskRowVO> page(String line, String status, String name,
                                                String priority, int pageNum, int pageSize) {
        QueryWrapper qw = QueryWrapper.create();
        if (line != null && !line.isBlank()) {
            qw.and(TASK_MAIN.LINE.eq(line));
        }
        if (status != null && !status.isBlank()) {
            qw.and(TASK_MAIN.STATUS.eq(status));
        }
        if (name != null && !name.isBlank()) {
            qw.and(TASK_MAIN.NAME.like(name.trim()));
        }
        if (priority != null && !priority.isBlank()) {
            qw.and(TASK_MAIN.PRIORITY.eq(priority));
        }
        long total = taskMapper.selectCountByQuery(qw);
        List<TaskMain> rows = taskMapper.selectListByQuery(qw
                .orderBy(TASK_MAIN.PRIORITY.asc())
                .orderBy(TASK_MAIN.CREATE_TIME.desc())
                .offset((long) (pageNum - 1) * pageSize).limit(pageSize));
        List<TaskRowVO> data = new ArrayList<>(rows.size());
        for (TaskMain t : rows) {
            TaskRowVO row = new TaskRowVO();
            BeanUtils.copyProperties(toVO(t), row);
            MatBatch b = t.getBatchId() == null ? null : batchMapper.selectOneById(t.getBatchId());
            row.setBatchBizNo(b == null ? null : b.getBizNo());
            row.setBatchName(b == null ? null : b.getName());
            row.setDatasetCount(datasetMapper.selectCountByQuery(QueryWrapper.create()
                    .where(DATASET.TASK_ID.eq(t.getId()))));
            data.add(row);
        }
        return PageResult.of(total, pageNum, pageSize, data);
    }

    /** 任务详情：任务 + 环节执行 + 数据集 + 复核单 + 参数快照。 */
    public TaskDetailVO detail(Long id) {
        TaskMain task = load(id);
        TaskDetailVO detail = new TaskDetailVO();
        BeanUtils.copyProperties(toVO(task), detail);
        detail.setStageNames(LineRegistry.STAGE_NAMES.get(task.getLine()));
        detail.setParamSnapshot(task.getParamSnapshot() == null ? List.of()
                : com.wbdz.common.JsonUtil.readList(task.getParamSnapshot()));
        detail.setRunning(orchestrator.isRunning(id));

        MatBatch batch = task.getBatchId() == null ? null : batchMapper.selectOneById(task.getBatchId());
        if (batch != null) {
            TaskDetailVO.Batch batchView = new TaskDetailVO.Batch();
            batchView.setId(batch.getId());
            batchView.setBizNo(batch.getBizNo());
            batchView.setName(batch.getName());
            batchView.setFileCount(batch.getFileCount() == null ? 0 : batch.getFileCount());
            detail.setBatch(batchView);
        }

        List<TaskDetailVO.StageRun> runs = new ArrayList<>();
        for (TaskStageRun runRow : stageRunMapper.selectListByQuery(QueryWrapper.create()
                .where(TASK_STAGE_RUN.TASK_ID.eq(id)).orderBy(TASK_STAGE_RUN.ID.asc()))) {
            TaskDetailVO.StageRun run = new TaskDetailVO.StageRun();
            run.setId(runRow.getId());
            run.setStageNo(runRow.getStageNo());
            run.setStageName(runRow.getStageName());
            run.setOperatorTag(runRow.getOperatorTag());
            run.setStatus(runRow.getStatus());
            run.setAttempt(runRow.getAttempt());
            run.setSummary(runRow.getSummary() == null ? null : com.wbdz.common.JsonUtil.readMap(runRow.getSummary()));
            run.setSkipped(runRow.getSkipped() == null ? List.of() : com.wbdz.common.JsonUtil.readList(runRow.getSkipped()));
            run.setFailed(runRow.getFailed() == null ? List.of() : com.wbdz.common.JsonUtil.readList(runRow.getFailed()));
            run.setStartTime(String.valueOf(runRow.getStartTime()));
            run.setEndTime(String.valueOf(runRow.getEndTime()));
            run.setProgress(operatorClient.readProgress(runRow.getId()));
            runs.add(run);
        }
        detail.setStageRuns(runs);

        detail.setDatasets(datasetMapper.selectListByQuery(QueryWrapper.create()
                        .where(DATASET.TASK_ID.eq(id)).orderBy(DATASET.ID.desc())).stream()
                .map(this::datasetBrief).toList());

        detail.setReviewOrders(reviewOrderMapper.selectListByQuery(QueryWrapper.create()
                        .where(REVIEW_ORDER.TASK_ID.eq(id)).orderBy(REVIEW_ORDER.ID.desc())).stream()
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

    private TaskDetailVO.DatasetBrief datasetBrief(Dataset dataset) {
        TaskDetailVO.DatasetBrief brief = new TaskDetailVO.DatasetBrief();
        brief.setId(dataset.getId());
        brief.setBizNo(dataset.getBizNo());
        brief.setSemVer(dataset.getSemVer());
        brief.setStatus(dataset.getStatus());
        brief.setItemCount(dataset.getItemCount());
        brief.setSkipCount(dataset.getSkipCount());
        brief.setCreateTime(String.valueOf(dataset.getCreateTime()));
        return brief;
    }
    // ==================== 内部 ====================

    private TaskMain load(Long id) {
        TaskMain task = taskMapper.selectOneById(id);
        if (task == null) {
            throw new BizException("任务不存在");
        }
        return task;
    }

    private ParamVersion resolveParam(String line, String version) {
        ParamVersion v = version == null || version.isBlank()
                ? paramService.latest(line)
                : paramVersionMapper.selectOneByQuery(QueryWrapper.create()
                        .where(PARAM_VERSION.LINE.eq(line))
                        .and(PARAM_VERSION.VERSION.eq(version)));
        if (v == null) {
            throw new BizException("该产线尚无已发布参数版本，请先在参数配置中发布");
        }
        return v;
    }

    /** 任务下已出结论的复核条目数（阈值锁定判定）。 */
    private Long reviewItemConcludedCount(Long taskId) {
        return reviewItemMapper.selectCountByQuery(QueryWrapper.create()
                .where(REVIEW_ITEM.TASK_ID.eq(taskId))
                .and(REVIEW_ITEM.CONCLUSION.isNotNull()));
    }

    private TaskVO toVO(TaskMain task) {
        TaskVO vo = TaskVO.from(task);
        vo.setLineName(LineRegistry.LINE_NAMES.get(task.getLine()));
        vo.setStatusName(STATUS_NAMES.get(task.getStatus()));
        return vo;
    }

    private void require(boolean cond, String msg) {
        if (!cond) {
            throw new BizException(msg);
        }
    }
}
