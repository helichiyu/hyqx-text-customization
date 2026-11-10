package com.wbdz.service.impl;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.service.DatasetService;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.AuthContext;
import com.wbdz.service.DatasetService;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.BizException;
import com.wbdz.service.DatasetService;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.BizId;
import com.wbdz.service.DatasetService;
import com.wbdz.service.LineRegistry;
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
import com.wbdz.vo.DatasetDeliveryRowVO;
import com.wbdz.vo.DatasetDetailVO;
import com.wbdz.vo.DatasetVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
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
public class DatasetServiceImpl implements DatasetService {


    private final DatasetMapper datasetMapper;

    private final DatasetItemMapper itemMapper;

    private final ReviewOrderMapper reviewOrderMapper;

    private final ReviewItemMapper reviewItemMapper;

    private final TaskMainMapper taskMapper;

    private final TaskStageRunMapper stageRunMapper;

    private final DeliveryLogMapper deliveryLogMapper;

    private final RollbackLogMapper rollbackLogMapper;

    public Long resolveId(String reference) {
        String ref = reference == null ? "" : reference.trim();
        if (ref.matches("\\d+")) {
            try {
                return Long.valueOf(ref);
            } catch (NumberFormatException e) {
                throw new BizException("数据集引用格式错误", e);
            }
        }
        Dataset dataset = datasetMapper.selectOneByQuery(QueryWrapper.create()
                .where(DATASET.BIZ_NO.eq(ref)));
        if (dataset == null) {
            throw new BizException("数据集不存在");
        }
        return dataset.getId();
    }
    // ==================== 查询 ====================

    public PageResult<DatasetVO> page(String line, String status, String keyword,
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
        return PageResult.of(total, pageNum, pageSize, rows.stream().map(this::toVO).toList());
    }

    /** 数据集详情（含明细分页、来源任务、交付/回滚记录）。 */
    public DatasetDetailVO detail(Long id, String reviewStatus, int pageNum, int pageSize) {
        Dataset dataset = load(id);
        DatasetDetailVO detail = new DatasetDetailVO();
        BeanUtils.copyProperties(toVO(dataset), detail);
        TaskMain task = dataset.getTaskId() == null ? null : taskMapper.selectOneById(dataset.getTaskId());
        if (task == null) {
            throw new BizException("数据集来源任务不存在");
        }
        {
            DatasetDetailVO.TaskBrief taskBrief = new DatasetDetailVO.TaskBrief();
            taskBrief.setId(task.getId());
            taskBrief.setBizNo(task.getBizNo());
            taskBrief.setName(task.getName());
            taskBrief.setLine(task.getLine());
            taskBrief.setThreshold(task.getThreshold());
            detail.setTask(taskBrief);
        }

        Long runId;
        Long imageRunId = null;
        if ("layout".equals(dataset.getLine())) {
            TaskStageRun detect = latestDoneRun(task.getId(), "lay_page_detect");
            TaskStageRun render = latestDoneRun(task.getId(), "lay_page_render");
            runId = detect == null ? null : detect.getId();
            imageRunId = render == null ? null : render.getId();
        } else {
            TaskStageRun lastRun = latestDoneRun(task.getId(), null);
            runId = lastRun == null ? null : lastRun.getId();
        }
        detail.setRunId(runId);
        detail.setImageRunId(imageRunId);

        QueryWrapper qw = QueryWrapper.create().where(DATASET_ITEM.DATASET_ID.eq(id));
        if (reviewStatus != null && !reviewStatus.isBlank()) {
            qw.and(DATASET_ITEM.REVIEW_STATUS.eq(reviewStatus));
        }
        long total = itemMapper.selectCountByQuery(qw);
        List<DatasetItem> items = itemMapper.selectListByQuery(qw
                .orderBy(DATASET_ITEM.ID.asc())
                .offset((long) (pageNum - 1) * pageSize).limit(pageSize));
        detail.setItems(PageResult.of(total, pageNum, pageSize,
                items.stream().map(this::itemVO).toList()));

        detail.setDeliveries(deliveryLogMapper.selectListByQuery(QueryWrapper.create()
                        .where(DELIVERY_LOG.DATASET_ID.eq(id)).orderBy(DELIVERY_LOG.ID.desc())).stream()
                .map(logRow -> {
                    DatasetDetailVO.Delivery delivery = new DatasetDetailVO.Delivery();
                    delivery.setBizNo(logRow.getBizNo());
                    delivery.setType(logRow.getType());
                    delivery.setFilename(logRow.getFilename());
                    delivery.setOperator(logRow.getOperator());
                    delivery.setTime(String.valueOf(logRow.getCreateTime()));
                    return delivery;
                }).toList());
        detail.setRollbacks(rollbackLogMapper.selectListByQuery(QueryWrapper.create()
                        .where(ROLLBACK_LOG.DATASET_ID.eq(id)).orderBy(ROLLBACK_LOG.ID.desc())).stream()
                .map(logRow -> {
                    DatasetDetailVO.Rollback rollback = new DatasetDetailVO.Rollback();
                    rollback.setBizNo(logRow.getBizNo());
                    rollback.setTarget(logRow.getTarget());
                    rollback.setReason(logRow.getReason());
                    rollback.setOperator(logRow.getOperator());
                    rollback.setTime(String.valueOf(logRow.getCreateTime()));
                    return rollback;
                }).toList());
        return detail;
    }
    // ==================== 发布 / 回滚 / 报告 ====================

    /** 发布：候选 → 已发布；要求来源任务所有复核单已闭环（done/void）。 */
    @Transactional(rollbackFor = Exception.class)
    public DatasetVO publish(Long id) {
        Dataset ds = load(id);
        require("candidate".equals(ds.getStatus()), "仅候选数据集可发布");
        TaskMain task = ds.getTaskId() == null ? null : taskMapper.selectOneById(ds.getTaskId());
        require(task != null, "来源任务不存在，不能发布数据集");
        Long open = reviewOrderMapper.selectCountByQuery(QueryWrapper.create()
                .where(REVIEW_ORDER.TASK_ID.eq(ds.getTaskId()))
                .and(REVIEW_ORDER.STATUS.in("pending", "doing")));
        require(open == 0, "来源任务还有未闭环复核单，不能发布");
        require("quality".equals(task.getStatus()) || "collected".equals(task.getStatus()),
                "来源任务尚未进入待归集，不能发布数据集");
        ds.setStatus("published");
        ds.setPublishBy(AuthContext.username());
        ds.setPublishTime(LocalDateTime.now());
        datasetMapper.update(ds);
        // 数据集发布即代表来源任务已经完成归集，保持工作台状态同步。
        if ("quality".equals(task.getStatus())) {
            task.setStatus("collected");
            taskMapper.update(task);
        }
        return toVO(ds);
    }

    /** 回滚：已发布 → 已回滚（原因必填，留痕）。 */
    @Transactional(rollbackFor = Exception.class)
    public DatasetVO rollback(Long id, String reason) {
        Dataset ds = load(id);
        require("published".equals(ds.getStatus()), "仅已发布数据集可回滚");
        require(reason != null && !reason.isBlank(), "回滚原因必填");
        ds.setStatus("rolledback");
        ds.setRollbackTime(LocalDateTime.now());
        datasetMapper.update(ds);
        RollbackLog logRow = new RollbackLog();
        String prefix = LineRegistry.LINE_PREFIX.get(ds.getLine());
        logRow.setBizNo(BizId.nextUnique(prefix, candidate -> rollbackLogMapper.selectCountByQuery(
                QueryWrapper.create().where(ROLLBACK_LOG.BIZ_NO.eq(candidate))) > 0));
        logRow.setDatasetId(id);
        logRow.setTarget("下线");
        logRow.setReason(reason.trim());
        logRow.setOperator(AuthContext.username());
        rollbackLogMapper.insert(logRow);
        return toVO(ds);
    }

    /**
     * 质量报告 TXT：仅已发布可下载；严格按交付说明 §十模板输出，
     * 仅含处理信息与质量结论、不含原始数据；每次下载记录交付（业务编号用产线前缀）。
     */
    @Transactional(rollbackFor = Exception.class)
    public DatasetService.ReportFile report(Long id) {
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
                : ds.getPublishTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
        LocalDateTime generatedAt = LocalDateTime.now();
        String now = generatedAt.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
        String qualityVersion = qualityVersionText(ds.getSemVer(), closed, confirmed, revised, excluded);

        String text = """
                数据集质量报告
                生成时间：%s
                数据集版本ID：%s
                质量版本号：%s
                所属产线：%s
                来源任务：%s
                内容条数：%s 条（已剔除条件复核 C 跳过 %d 条）
                发布状态：已发布（%s）
                条件复核：未闭环 %d 个，已闭环 %d 个
                复核处置：A确认 %d 条 / B修正 %d 条 / C剔除 %d 条
                说明：条件复核覆盖系统分流的争议条目，不表示全部数据经人工逐条检查。
                数据范围：本报告仅含处理信息与质量结论，不含原始数据（本系统数据不出域）。
                """.formatted(now, ds.getBizNo(), qualityVersion, lineName, taskText,
                String.format("%,d", contentCount), cCount, publishTime, open, closed,
                confirmed, revised, excluded);
        String stamp = generatedAt.format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String filename = ds.getBizNo() + "_质量报告_" + stamp + ".txt";
        DeliveryLog logRow = new DeliveryLog();
        String prefix = LineRegistry.LINE_PREFIX.get(ds.getLine());
        logRow.setBizNo(BizId.nextUnique(prefix, candidate -> deliveryLogMapper.selectCountByQuery(
                QueryWrapper.create().where(DELIVERY_LOG.BIZ_NO.eq(candidate))) > 0));
        logRow.setDatasetId(id);
        logRow.setType("质量报告TXT");
        logRow.setFilename(filename);
        logRow.setOperator(AuthContext.username());
        deliveryLogMapper.insert(logRow);
        log.info("质量报告下载: dataset={} content={} A/B/C={}/{}/{} by={}", ds.getBizNo(),
                contentCount, confirmed, revised, excluded, AuthContext.username());
        return new DatasetService.ReportFile(filename, text.getBytes(StandardCharsets.UTF_8));
    }

    /** 质量版本说明：V1 直出、V2 复核闭环、V3 起重跑。 */
    private String qualityVersionText(String semVer, long closed,
                                      long confirmed, long revised, long excluded) {
        int major = 1;
        if (semVer != null && semVer.matches("V\\d+\\.0")) {
            major = Integer.parseInt(semVer.substring(1, semVer.indexOf('.')));
        }
        List<String> factors = new ArrayList<>();
        if (major >= 3) factors.add("成片错误重跑（第" + (major - 2) + "次）产出");
        if (closed > 0) factors.add("经条件复核闭环：确认" + confirmed + " / 修正" + revised + " / 跳过" + excluded);
        if (factors.isEmpty()) factors.add("产线直出");
        return semVer + "（" + String.join("；", factors) + "）";
    }

    /** 交付记录分页。 */
    public PageResult<DatasetDeliveryRowVO> deliveries(int pageNum, int pageSize) {
        long total = deliveryLogMapper.selectCountByQuery(QueryWrapper.create());
        List<DeliveryLog> rows = deliveryLogMapper.selectListByQuery(QueryWrapper.create()
                .orderBy(DELIVERY_LOG.ID.desc())
                .offset((long) (pageNum - 1) * pageSize).limit(pageSize));
        List<DatasetDeliveryRowVO> data = new ArrayList<>(rows.size());
        for (DeliveryLog logRow : rows) {
            DatasetDeliveryRowVO row = new DatasetDeliveryRowVO();
            row.setBizNo(logRow.getBizNo());
            row.setDatasetId(logRow.getDatasetId());
            Dataset dataset = logRow.getDatasetId() == null ? null : datasetMapper.selectOneById(logRow.getDatasetId());
            row.setDatasetBizNo(dataset == null ? null : dataset.getBizNo());
            row.setLineName(dataset == null ? null : LineRegistry.LINE_NAMES.get(dataset.getLine()));
            row.setType(logRow.getType());
            row.setFilename(logRow.getFilename());
            row.setOperator(logRow.getOperator());
            row.setTime(String.valueOf(logRow.getCreateTime()));
            data.add(row);
        }
        return PageResult.of(total, pageNum, pageSize, data);
    }

    private Dataset load(Long id) {
        Dataset dataset = datasetMapper.selectOneById(id);
        if (dataset == null) {
            throw new BizException("数据集不存在");
        }
        return dataset;
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
    // ==================== 视图 ====================

    private DatasetVO toVO(Dataset dataset) {
        DatasetVO vo = DatasetVO.from(dataset);
        vo.setLineName(LineRegistry.LINE_NAMES.get(dataset.getLine()));
        vo.setStatusName(STATUS_NAMES.get(dataset.getStatus()));
        return vo;
    }

    private DatasetDetailVO.Item itemVO(DatasetItem item) {
        DatasetDetailVO.Item vo = new DatasetDetailVO.Item();
        vo.setId(item.getId());
        vo.setItemKey(item.getItemKey());
        vo.setPayload(item.getPayload() == null ? null : com.wbdz.common.JsonUtil.readMap(item.getPayload()));
        vo.setReviewStatus(item.getReviewStatus());
        vo.setRevisionStatus(item.getRevisionStatus());
        vo.setConfidence(item.getConfidence());
        return vo;
    }
    private void require(boolean cond, String msg) {
        if (!cond) {
            throw new BizException(msg);
        }
    }
}
