package com.wbdz.service;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.common.AuthContext;
import com.wbdz.common.BizException;
import com.wbdz.common.BizId;
import com.wbdz.common.PageResult;
import com.wbdz.entity.Dataset;
import com.wbdz.entity.DatasetItem;
import com.wbdz.entity.DeliveryLog;
import com.wbdz.entity.ReviewItem;
import com.wbdz.entity.ReviewOrder;
import com.wbdz.entity.RollbackLog;
import com.wbdz.entity.TaskMain;
import com.wbdz.entity.TaskStageRun;
import com.wbdz.mapper.DatasetItemMapper;
import com.wbdz.mapper.DatasetMapper;
import com.wbdz.mapper.DeliveryLogMapper;
import com.wbdz.mapper.ReviewItemMapper;
import com.wbdz.mapper.ReviewOrderMapper;
import com.wbdz.mapper.RollbackLogMapper;
import com.wbdz.mapper.TaskMainMapper;
import com.wbdz.mapper.TaskStageRunMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static com.wbdz.entity.table.DatasetItemTableDef.DATASET_ITEM;
import static com.wbdz.entity.table.DatasetTableDef.DATASET;
import static com.wbdz.entity.table.DeliveryLogTableDef.DELIVERY_LOG;
import static com.wbdz.entity.table.ReviewItemTableDef.REVIEW_ITEM;
import static com.wbdz.entity.table.ReviewOrderTableDef.REVIEW_ORDER;
import static com.wbdz.entity.table.RollbackLogTableDef.ROLLBACK_LOG;
import static com.wbdz.entity.table.TaskStageRunTableDef.TASK_STAGE_RUN;

/**
 * 数据集管理：候选 → 发布（要求来源任务复核单全部闭环）→ 回滚（原因必填）；
 * 质检报告 TXT 下载（仅已发布，记录交付）；语义版本 V1.0 直出 / V2.0 复核闭环 / 重跑 +1。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DatasetService {

    /** 数据集状态中文名。 */
    public static final Map<String, String> STATUS_NAMES = Map.of(
            "candidate", "候选", "published", "已发布", "rolledback", "已回滚");

    private final DatasetMapper datasetMapper;

    private final DatasetItemMapper itemMapper;

    private final ReviewOrderMapper reviewOrderMapper;

    private final ReviewItemMapper reviewItemMapper;

    private final TaskMainMapper taskMapper;

    private final TaskStageRunMapper stageRunMapper;

    private final DeliveryLogMapper deliveryLogMapper;

    private final RollbackLogMapper rollbackLogMapper;

    // ==================== 查询 ====================

    public PageResult<Map<String, Object>> page(String line, String status, String keyword,
                                                int pageNum, int pageSize) {
        QueryWrapper qw = QueryWrapper.create();
        if (line != null && !line.isBlank()) {
            qw.and(DATASET.LINE.eq(line));
        }
        if (status != null && !status.isBlank()) {
            qw.and(DATASET.STATUS.eq(status));
        }
        if (keyword != null && !keyword.isBlank()) {
            qw.and(DATASET.BIZ_NO.like(keyword.trim()));
        }
        long total = datasetMapper.selectCountByQuery(qw);
        List<Dataset> rows = datasetMapper.selectListByQuery(qw
                .orderBy(DATASET.CREATE_TIME.desc())
                .offset((long) (pageNum - 1) * pageSize).limit(pageSize));
        return PageResult.of(total, pageNum, pageSize, rows.stream().map(this::toView).toList());
    }

    /** 数据集详情（含明细分页、来源任务、交付/回滚记录）。 */
    public Map<String, Object> detail(Long id, String reviewStatus, int pageNum, int pageSize) {
        Dataset ds = load(id);
        Map<String, Object> m = toView(ds);
        TaskMain task = ds.getTaskId() == null ? null : taskMapper.selectOneById(ds.getTaskId());
        m.put("task", task == null ? null : Map.of(
                "id", task.getId(), "bizNo", task.getBizNo(), "name", task.getName(),
                "line", task.getLine(), "threshold", task.getThreshold() == null ? "" : task.getThreshold()));

        // 数据集明细的页图预览：版面页图（lay_page_render）与框选图层（lay_page_detect）
        // 分属两次执行，分别定位；其它产线取最近一次成功执行（暂无图片依赖）。
        Long runId = null;
        Long imageRunId = null;
        if ("layout".equals(ds.getLine())) {
            TaskStageRun detect = latestDoneRun(task.getId(), "lay_page_detect");
            TaskStageRun render = latestDoneRun(task.getId(), "lay_page_render");
            runId = detect == null ? null : detect.getId();
            imageRunId = render == null ? null : render.getId();
        } else {
            TaskStageRun lastRun = latestDoneRun(task.getId(), null);
            runId = lastRun == null ? null : lastRun.getId();
        }
        m.put("runId", runId);
        m.put("imageRunId", imageRunId);

        QueryWrapper qw = QueryWrapper.create().where(DATASET_ITEM.DATASET_ID.eq(id));
        if (reviewStatus != null && !reviewStatus.isBlank()) {
            qw.and(DATASET_ITEM.REVIEW_STATUS.eq(reviewStatus));
        }
        long total = itemMapper.selectCountByQuery(qw);
        List<DatasetItem> items = itemMapper.selectListByQuery(qw
                .orderBy(DATASET_ITEM.ID.asc())
                .offset((long) (pageNum - 1) * pageSize).limit(pageSize));
        m.put("items", PageResult.of(total, pageNum, pageSize,
                items.stream().map(this::itemView).toList()));

        m.put("deliveries", deliveryLogMapper.selectListByQuery(QueryWrapper.create()
                        .where(DELIVERY_LOG.DATASET_ID.eq(id)).orderBy(DELIVERY_LOG.ID.desc())).stream()
                .map(d -> Map.of("bizNo", d.getBizNo(), "type", d.getType(), "filename", d.getFilename(),
                        "operator", d.getOperator(), "time", String.valueOf(d.getCreateTime()))).toList());
        m.put("rollbacks", rollbackLogMapper.selectListByQuery(QueryWrapper.create()
                        .where(ROLLBACK_LOG.DATASET_ID.eq(id)).orderBy(ROLLBACK_LOG.ID.desc())).stream()
                .map(r -> Map.of("bizNo", r.getBizNo(), "target", r.getTarget(), "reason", r.getReason(),
                        "operator", r.getOperator(), "time", String.valueOf(r.getCreateTime()))).toList());
        return m;
    }

    // ==================== 发布 / 回滚 / 报告 ====================

    /** 发布：候选 → 已发布；要求来源任务所有复核单已闭环（done/void）。 */
    @Transactional(rollbackFor = Exception.class)
    public Dataset publish(Long id) {
        Dataset ds = load(id);
        require("candidate".equals(ds.getStatus()), "仅候选数据集可发布");
        Long open = reviewOrderMapper.selectCountByQuery(QueryWrapper.create()
                .where(REVIEW_ORDER.TASK_ID.eq(ds.getTaskId()))
                .and(REVIEW_ORDER.STATUS.in("pending", "doing")));
        require(open == 0, "来源任务还有未闭环复核单，不能发布");
        ds.setStatus("published");
        ds.setPublishBy(AuthContext.username());
        ds.setPublishTime(LocalDateTime.now());
        datasetMapper.update(ds);
        return ds;
    }

    /** 回滚：已发布 → 已回滚（原因必填，留痕）。 */
    @Transactional(rollbackFor = Exception.class)
    public Dataset rollback(Long id, String reason) {
        Dataset ds = load(id);
        require("published".equals(ds.getStatus()), "仅已发布数据集可回滚");
        require(reason != null && !reason.isBlank(), "回滚原因必填");
        ds.setStatus("rolledback");
        ds.setRollbackTime(LocalDateTime.now());
        datasetMapper.update(ds);
        RollbackLog logRow = new RollbackLog();
        logRow.setBizNo(BizId.next(LineRegistry.LINE_PREFIX.get(ds.getLine())));
        logRow.setDatasetId(id);
        logRow.setTarget("下线");
        logRow.setReason(reason.trim());
        logRow.setOperator(AuthContext.username());
        rollbackLogMapper.insert(logRow);
        return ds;
    }

    /**
     * 质量报告 TXT：仅已发布可下载；严格按交付说明 §十模板输出，
     * 仅含处理信息与质量结论、不含原始数据；每次下载记录交付（业务编号用产线前缀）。
     */
    @Transactional(rollbackFor = Exception.class)
    public ReportFile report(Long id) {
        Dataset ds = load(id);
        require("published".equals(ds.getStatus()), "仅已发布数据集可下载质量报告");
        TaskMain task = ds.getTaskId() == null ? null : taskMapper.selectOneById(ds.getTaskId());

        List<ReviewOrder> orders = reviewOrderMapper.selectListByQuery(QueryWrapper.create()
                .where(REVIEW_ORDER.TASK_ID.eq(ds.getTaskId())));
        long open = orders.stream()
                .filter(o -> "pending".equals(o.getStatus()) || "doing".equals(o.getStatus())).count();
        long closed = orders.stream().filter(o -> "done".equals(o.getStatus())).count();

        // 作废单（重跑产生）不计入复核处置；A/B/C 按有效复核单的条目统计。
        List<Long> effectiveOrderIds = orders.stream()
                .filter(o -> !"void".equals(o.getStatus()))
                .map(ReviewOrder::getId).toList();
        long confirmed = 0;
        long revised = 0;
        long excluded = 0;
        if (!effectiveOrderIds.isEmpty()) {
            List<ReviewItem> items = reviewItemMapper.selectListByQuery(QueryWrapper.create()
                    .where(REVIEW_ITEM.ORDER_ID.in(effectiveOrderIds)));
            confirmed = items.stream().filter(i -> "A".equals(i.getConclusion())).count();
            revised = items.stream().filter(i -> "B".equals(i.getConclusion())).count();
            excluded = items.stream().filter(i -> "C".equals(i.getConclusion())).count();
        }

        int contentCount = ds.getItemCount() == null ? 0 : ds.getItemCount();
        int cCount = ds.getSkipCount() == null ? 0 : ds.getSkipCount();
        String lineName = LineRegistry.LINE_NAMES.getOrDefault(ds.getLine(), ds.getLine());
        String taskText = task == null ? "-" : task.getBizNo() + " " + task.getName();
        String publishTime = ds.getPublishTime() == null ? "-"
                : ds.getPublishTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        String now = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));

        String text = """
                数据集质量报告
                生成时间：%s
                数据集版本ID：%s
                质量版本号：%s
                所属产线：%s
                来源任务：%s
                内容条数：%d 条（已剔除条件复核 C 跳过 %d 条）
                发布状态：已发布（%s）
                条件复核：未闭环 %d 个，已闭环 %d 个
                复核处置：A确认 %d 条 / B修正 %d 条 / C剔除 %d 条
                说明：条件复核覆盖系统分流的争议条目，不表示全部数据经人工逐条检查。
                数据范围：本报告仅含处理信息与质量结论，不含原始数据（本系统数据不出域）。
                """.formatted(now, ds.getBizNo(), ds.getSemVer(), lineName, taskText,
                contentCount, cCount, publishTime, open, closed, confirmed, revised, excluded);
        String filename = "质量报告_" + ds.getBizNo() + "_" + ds.getSemVer() + ".txt";
        DeliveryLog logRow = new DeliveryLog();
        logRow.setBizNo(BizId.next(LineRegistry.LINE_PREFIX.get(ds.getLine())));
        logRow.setDatasetId(id);
        logRow.setType("质量报告TXT");
        logRow.setFilename(filename);
        logRow.setOperator(AuthContext.username());
        deliveryLogMapper.insert(logRow);
        log.info("质量报告下载: dataset={} content={} A/B/C={}/{}/{} by={}", ds.getBizNo(),
                contentCount, confirmed, revised, excluded, AuthContext.username());
        return new ReportFile(filename, text.getBytes(StandardCharsets.UTF_8));
    }

    /** 交付记录分页。 */
    public PageResult<Map<String, Object>> deliveries(int pageNum, int pageSize) {
        long total = deliveryLogMapper.selectCountByQuery(QueryWrapper.create());
        List<DeliveryLog> rows = deliveryLogMapper.selectListByQuery(QueryWrapper.create()
                .orderBy(DELIVERY_LOG.ID.desc())
                .offset((long) (pageNum - 1) * pageSize).limit(pageSize));
        List<Map<String, Object>> data = new ArrayList<>(rows.size());
        for (DeliveryLog d : rows) {
            Map<String, Object> m = new LinkedHashMap<String, Object>();
            m.put("bizNo", d.getBizNo());
            m.put("datasetId", d.getDatasetId());
            Dataset ds = d.getDatasetId() == null ? null : datasetMapper.selectOneById(d.getDatasetId());
            m.put("datasetBizNo", ds == null ? null : ds.getBizNo());
            m.put("lineName", ds == null ? null : LineRegistry.LINE_NAMES.get(ds.getLine()));
            m.put("type", d.getType());
            m.put("filename", d.getFilename());
            m.put("operator", d.getOperator());
            m.put("time", String.valueOf(d.getCreateTime()));
            data.add(m);
        }
        return PageResult.of(total, pageNum, pageSize, data);
    }

    /** 报告文件（文件名 + 字节）。 */
    public record ReportFile(String filename, byte[] bytes) {
    }

    // ==================== 视图 ====================

    private Map<String, Object> toView(Dataset d) {
        Map<String, Object> m = new LinkedHashMap<String, Object>();
        m.put("id", d.getId());
        m.put("bizNo", d.getBizNo());
        m.put("line", d.getLine());
        m.put("lineName", LineRegistry.LINE_NAMES.get(d.getLine()));
        m.put("taskId", d.getTaskId());
        m.put("itemCount", d.getItemCount());
        m.put("skipCount", d.getSkipCount());
        m.put("semVer", d.getSemVer());
        m.put("status", d.getStatus());
        m.put("statusName", STATUS_NAMES.get(d.getStatus()));
        m.put("publishBy", d.getPublishBy());
        m.put("publishTime", String.valueOf(d.getPublishTime()));
        m.put("createTime", String.valueOf(d.getCreateTime()));
        return m;
    }

    private Map<String, Object> itemView(DatasetItem i) {
        Map<String, Object> m = new LinkedHashMap<String, Object>();
        m.put("id", i.getId());
        m.put("itemKey", i.getItemKey());
        m.put("payload", i.getPayload() == null ? null : com.wbdz.common.JsonUtil.readMap(i.getPayload()));
        m.put("reviewStatus", i.getReviewStatus());
        m.put("revisionStatus", i.getRevisionStatus());
        m.put("confidence", i.getConfidence());
        return m;
    }

    /** 任务最近一次成功的环节执行记录；tag 为 null 时不限算子。 */
    private TaskStageRun latestDoneRun(Long taskId, String tag) {
        QueryWrapper qw = QueryWrapper.create()
                .where(TASK_STAGE_RUN.TASK_ID.eq(taskId))
                .and(TASK_STAGE_RUN.STATUS.eq("done"));
        if (tag != null) {
            qw.and(TASK_STAGE_RUN.OPERATOR_TAG.eq(tag));
        }
        return stageRunMapper.selectOneByQuery(qw.orderBy(TASK_STAGE_RUN.ID.desc()).limit(1));
    }

    private Dataset load(Long id) {
        Dataset ds = datasetMapper.selectOneById(id);
        if (ds == null) {
            throw new BizException("数据集不存在");
        }
        return ds;
    }

    private void require(boolean cond, String msg) {
        if (!cond) {
            throw new BizException(msg);
        }
    }
}
