package com.wbdz.service;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.common.AuthContext;
import com.wbdz.common.BizException;
import com.wbdz.common.BizId;
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
import lombok.RequiredArgsConstructor;
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
public class TaskService {

    /** 状态中文名（展示统一口径）。 */
    public static final Map<String, String> STATUS_NAMES = Map.of(
            "draft", "草稿", "pending", "待处理", "processing", "加工中",
            "waitreview", "待复核", "quality", "待归集", "collected", "已归集", "reject", "已驳回");

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

    // ==================== 动作 ====================

    /** 创建任务（草稿；锁定参数版本快照）。 */
    @Transactional(rollbackFor = Exception.class)
    public TaskMain create(TaskCreateDTO dto) {
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
        task.setBizNo(BizId.next("TASK"));
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
        return task;
    }

    /** 修改草稿任务；重新校验批次、参数版本和图文大类。 */
    @Transactional(rollbackFor = Exception.class)
    public TaskMain update(Long id, TaskUpdateDTO dto) {
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
        return task;
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

    // ==================== 查询 ====================

    public PageResult<Map<String, Object>> page(String line, String status, String name,
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
        List<Map<String, Object>> data = new ArrayList<>(rows.size());
        for (TaskMain t : rows) {
            Map<String, Object> m = toView(t);
            MatBatch b = t.getBatchId() == null ? null : batchMapper.selectOneById(t.getBatchId());
            m.put("batchBizNo", b == null ? null : b.getBizNo());
            m.put("batchName", b == null ? null : b.getName());
            Long ds = datasetMapper.selectCountByQuery(QueryWrapper.create()
                    .where(DATASET.TASK_ID.eq(t.getId())));
            m.put("datasetCount", ds);
            data.add(m);
        }
        return PageResult.of(total, pageNum, pageSize, data);
    }

    /** 任务详情：任务 + 环节执行 + 数据集 + 复核单 + 参数快照。 */
    public Map<String, Object> detail(Long id) {
        TaskMain task = load(id);
        Map<String, Object> m = toView(task);
        m.put("stageNames", LineRegistry.STAGE_NAMES.get(task.getLine()));
        m.put("paramSnapshot", task.getParamSnapshot() == null ? List.of()
                : com.wbdz.common.JsonUtil.readList(task.getParamSnapshot()));
        m.put("running", orchestrator.isRunning(id));

        MatBatch b = task.getBatchId() == null ? null : batchMapper.selectOneById(task.getBatchId());
        m.put("batch", b == null ? null : Map.of(
                "id", b.getId(), "bizNo", b.getBizNo(), "name", b.getName(),
                "fileCount", b.getFileCount() == null ? 0 : b.getFileCount()));

        List<Map<String, Object>> runs = new ArrayList<>();
        for (TaskStageRun r : stageRunMapper.selectListByQuery(QueryWrapper.create()
                .where(TASK_STAGE_RUN.TASK_ID.eq(id)).orderBy(TASK_STAGE_RUN.ID.asc()))) {
            Map<String, Object> rm = new LinkedHashMap<String, Object>();
            rm.put("id", r.getId());
            rm.put("stageNo", r.getStageNo());
            rm.put("stageName", r.getStageName());
            rm.put("operatorTag", r.getOperatorTag());
            rm.put("status", r.getStatus());
            rm.put("attempt", r.getAttempt());
            rm.put("summary", r.getSummary() == null ? null : com.wbdz.common.JsonUtil.readMap(r.getSummary()));
            rm.put("skipped", r.getSkipped() == null ? List.of() : com.wbdz.common.JsonUtil.readList(r.getSkipped()));
            rm.put("failed", r.getFailed() == null ? List.of() : com.wbdz.common.JsonUtil.readList(r.getFailed()));
            rm.put("startTime", String.valueOf(r.getStartTime()));
            rm.put("endTime", String.valueOf(r.getEndTime()));
            runs.add(rm);
        }
        m.put("stageRuns", runs);

        m.put("datasets", datasetMapper.selectListByQuery(QueryWrapper.create()
                        .where(DATASET.TASK_ID.eq(id)).orderBy(DATASET.ID.desc())).stream()
                .map(this::datasetBrief).toList());

        m.put("reviewOrders", reviewOrderMapper.selectListByQuery(QueryWrapper.create()
                        .where(REVIEW_ORDER.TASK_ID.eq(id)).orderBy(REVIEW_ORDER.ID.desc())).stream()
                .map(o -> {
                    Map<String, Object> om = new LinkedHashMap<String, Object>();
                    om.put("id", o.getId());
                    om.put("bizNo", o.getBizNo());
                    om.put("status", o.getStatus());
                    om.put("stageName", o.getStageName());
                    om.put("itemCount", o.getItemCount());
                    om.put("triggerDesc", o.getTriggerDesc());
                    return om;
                }).toList());
        return m;
    }

    private Map<String, Object> datasetBrief(Dataset d) {
        Map<String, Object> dm = new LinkedHashMap<String, Object>();
        dm.put("id", d.getId());
        dm.put("bizNo", d.getBizNo());
        dm.put("semVer", d.getSemVer());
        dm.put("status", d.getStatus());
        dm.put("itemCount", d.getItemCount());
        dm.put("skipCount", d.getSkipCount());
        dm.put("createTime", String.valueOf(d.getCreateTime()));
        return dm;
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

    private Map<String, Object> toView(TaskMain t) {
        Map<String, Object> m = new LinkedHashMap<String, Object>();
        m.put("id", t.getId());
        m.put("bizNo", t.getBizNo());
        m.put("name", t.getName());
        m.put("line", t.getLine());
        m.put("lineName", LineRegistry.LINE_NAMES.get(t.getLine()));
        m.put("status", t.getStatus());
        m.put("statusName", STATUS_NAMES.get(t.getStatus()));
        m.put("priority", t.getPriority());
        m.put("imageClass", t.getImageClass());
        m.put("batchId", t.getBatchId());
        m.put("paramVersion", t.getParamVersion());
        m.put("threshold", t.getThreshold());
        m.put("currentStage", t.getCurrentStage());
        m.put("createBy", t.getCreateBy());
        m.put("createTime", String.valueOf(t.getCreateTime()));
        return m;
    }

    private void require(boolean cond, String msg) {
        if (!cond) {
            throw new BizException(msg);
        }
    }
}
