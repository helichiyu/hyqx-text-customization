package com.hsmty.tcs.service.impl;

import com.hsmty.core.common.entity.PageResult;
import com.hsmty.core.util.BeanCopyUtils;
import com.hsmty.core.util.JsonUtils;
import com.hsmty.core.util.PageUtils;
import com.hsmty.tcs.common.AuthContext;
import com.hsmty.tcs.common.BizException;
import com.hsmty.tcs.common.BizId;
import com.hsmty.tcs.common.Times;
import com.hsmty.tcs.mapper.DatasetItemMapper;
import com.hsmty.tcs.mapper.DatasetMapper;
import com.hsmty.tcs.mapper.DeliveryLogMapper;
import com.hsmty.tcs.mapper.ReviewItemMapper;
import com.hsmty.tcs.mapper.ReviewOrderMapper;
import com.hsmty.tcs.mapper.RollbackLogMapper;
import com.hsmty.tcs.mapper.TaskMainMapper;
import com.hsmty.tcs.mapper.TaskStageRunMapper;
import com.hsmty.tcs.operator.LineRegistry;
import com.hsmty.tcs.pojo.dto.DatasetDetailDTO;
import com.hsmty.tcs.pojo.dto.DatasetListDTO;
import com.hsmty.tcs.pojo.dto.DeliveryListDTO;
import com.hsmty.tcs.pojo.po.DatasetEntity;
import com.hsmty.tcs.pojo.po.DatasetItemEntity;
import com.hsmty.tcs.pojo.po.DeliveryLogEntity;
import com.hsmty.tcs.pojo.po.ReviewItemEntity;
import com.hsmty.tcs.pojo.po.ReviewOrderEntity;
import com.hsmty.tcs.pojo.po.RollbackLogEntity;
import com.hsmty.tcs.pojo.po.TaskMainEntity;
import com.hsmty.tcs.pojo.po.TaskStageRunEntity;
import com.hsmty.tcs.pojo.vo.DatasetDeliveryRowVO;
import com.hsmty.tcs.pojo.vo.DatasetDetailVO;
import com.hsmty.tcs.pojo.vo.DatasetVO;
import com.hsmty.tcs.service.DatasetService;
import com.mybatisflex.core.paginate.Page;
import com.mybatisflex.core.query.QueryWrapper;
import com.mybatisflex.spring.service.impl.ServiceImpl;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * <p>数据集管理：候选 → 发布（要求来源任务复核单全部闭环）→ 回滚（原因必填）；
 * 质检报告 TXT 下载（仅已发布，记录交付）；语义版本 V1.0 直出 / V2.0 复核闭环 / 重跑 +1。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DatasetServiceImpl extends ServiceImpl<DatasetMapper, DatasetEntity>
        implements DatasetService {

    private static final DateTimeFormatter MINUTE =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    private static final DateTimeFormatter STAMP =
            DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");

    private final DatasetMapper datasetMapper;

    private final DatasetItemMapper itemMapper;

    private final ReviewOrderMapper reviewOrderMapper;

    private final ReviewItemMapper reviewItemMapper;

    private final TaskMainMapper taskMapper;

    private final TaskStageRunMapper stageRunMapper;

    private final DeliveryLogMapper deliveryLogMapper;

    private final RollbackLogMapper rollbackLogMapper;

    @Override
    public Long resolveId(String reference) {
        String ref = reference == null ? "" : reference.trim();
        if (ref.matches("\\d+")) {
            try {
                return Long.valueOf(ref);
            } catch (NumberFormatException e) {
                throw new BizException("数据集引用格式错误", e);
            }
        }
        DatasetEntity dataset = datasetMapper.selectOneByQuery(QueryWrapper.create()
                .where("biz_no = ?", ref));
        if (dataset == null) {
            throw new BizException("数据集不存在");
        }
        return dataset.getId();
    }

    // ==================== 查询 ====================

    @Override
    public PageResult<DatasetVO> page(DatasetListDTO dto) {
        QueryWrapper qw = QueryWrapper.create();
        if (dto.getLine() != null && !dto.getLine().isBlank()) {
            qw.and("line = ?", dto.getLine());
        }
        if (dto.getStatus() != null && !dto.getStatus().isBlank()) {
            qw.and("status = ?", dto.getStatus());
        }
        if (dto.getKeyword() != null && !dto.getKeyword().isBlank()) {
            qw.and("biz_no like ?", "%" + dto.getKeyword().trim() + "%");
        }
        qw.orderBy("create_time desc");
        Page<DatasetEntity> page = datasetMapper.paginate(PageUtils.getPage(dto), qw);
        return PageUtils.getPageResult(page.map(this::toVO));
    }

    /**
     * 数据集详情（含明细分页、来源任务、交付/回滚记录）。
     */
    @Override
    public DatasetDetailVO detail(Long id, DatasetDetailDTO dto) {
        DatasetEntity dataset = load(id);
        DatasetDetailVO detail = BeanCopyUtils.copy(toVO(dataset), DatasetDetailVO.class);
        TaskMainEntity task = dataset.getTaskId() == null
                ? null : taskMapper.selectOneById(dataset.getTaskId());
        if (task == null) {
            throw new BizException("数据集来源任务不存在");
        }
        DatasetDetailVO.TaskBrief taskBrief = new DatasetDetailVO.TaskBrief();
        taskBrief.setId(task.getId());
        taskBrief.setBizNo(task.getBizNo());
        taskBrief.setName(task.getName());
        taskBrief.setLine(task.getLine());
        taskBrief.setThreshold(task.getThreshold());
        detail.setTask(taskBrief);

        Long runId;
        Long imageRunId = null;
        if ("layout".equals(dataset.getLine())) {
            TaskStageRunEntity detect = latestDoneRun(task.getId(), "lay_page_detect");
            TaskStageRunEntity render = latestDoneRun(task.getId(), "lay_page_render");
            runId = detect == null ? null : detect.getId();
            imageRunId = render == null ? null : render.getId();
        } else {
            TaskStageRunEntity lastRun = latestDoneRun(task.getId(), null);
            runId = lastRun == null ? null : lastRun.getId();
        }
        detail.setRunId(runId);
        detail.setImageRunId(imageRunId);

        QueryWrapper qw = QueryWrapper.create().where("dataset_id = ?", id);
        if (dto.getReviewStatus() != null && !dto.getReviewStatus().isBlank()) {
            qw.and("review_status = ?", dto.getReviewStatus());
        }
        qw.orderBy("id asc");
        Page<DatasetItemEntity> itemPage = itemMapper.paginate(PageUtils.getPage(dto), qw);
        detail.setItems(PageUtils.getPageResult(itemPage.map(this::itemVO)));

        detail.setDeliveries(deliveryLogMapper.selectListByQuery(QueryWrapper.create()
                        .where("dataset_id = ?", id).orderBy("id desc")).stream()
                .map(logRow -> {
                    DatasetDetailVO.Delivery delivery = new DatasetDetailVO.Delivery();
                    delivery.setBizNo(logRow.getBizNo());
                    delivery.setType(logRow.getType());
                    delivery.setFilename(logRow.getFilename());
                    delivery.setOperator(logRow.getOperator());
                    delivery.setTime(Times.text(logRow.getCreateTime()));
                    return delivery;
                }).toList());
        detail.setRollbacks(rollbackLogMapper.selectListByQuery(QueryWrapper.create()
                        .where("dataset_id = ?", id).orderBy("id desc")).stream()
                .map(logRow -> {
                    DatasetDetailVO.Rollback rollback = new DatasetDetailVO.Rollback();
                    rollback.setBizNo(logRow.getBizNo());
                    rollback.setTarget(logRow.getTarget());
                    rollback.setReason(logRow.getReason());
                    rollback.setOperator(logRow.getOperator());
                    rollback.setTime(Times.text(logRow.getCreateTime()));
                    return rollback;
                }).toList());
        return detail;
    }

    // ==================== 发布 / 回滚 / 报告 ====================

    /**
     * 发布：候选 → 已发布；要求来源任务所有复核单已闭环（done/void）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public DatasetVO publish(Long id) {
        DatasetEntity ds = load(id);
        require("candidate".equals(ds.getStatus()), "仅候选数据集可发布");
        TaskMainEntity task = ds.getTaskId() == null ? null : taskMapper.selectOneById(ds.getTaskId());
        require(task != null, "来源任务不存在，不能发布数据集");
        Long open = reviewOrderMapper.selectCountByQuery(QueryWrapper.create()
                .where("task_id = ?", ds.getTaskId())
                .and("status in (?, ?)", "pending", "doing"));
        require(open == null || open == 0, "来源任务还有未闭环复核单，不能发布");
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

    /**
     * 回滚：已发布 → 已回滚（原因必填，留痕）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public DatasetVO rollback(Long id, String reason) {
        DatasetEntity ds = load(id);
        require("published".equals(ds.getStatus()), "仅已发布数据集可回滚");
        require(reason != null && !reason.isBlank(), "回滚原因必填");
        ds.setStatus("rolledback");
        ds.setRollbackTime(LocalDateTime.now());
        datasetMapper.update(ds);
        RollbackLogEntity logRow = new RollbackLogEntity();
        String prefix = LineRegistry.LINE_PREFIX.get(ds.getLine());
        logRow.setBizNo(BizId.nextUnique(prefix, candidate -> rollbackLogMapper.selectCountByQuery(
                QueryWrapper.create().where("biz_no = ?", candidate)) > 0));
        logRow.setDatasetId(id);
        logRow.setTarget("下线");
        logRow.setReason(reason.trim());
        logRow.setOperator(AuthContext.username());
        rollbackLogMapper.insert(logRow);
        return toVO(ds);
    }

    /**
     * 质量报告 TXT：仅已发布可下载；仅含处理信息与质量结论、不含原始数据；
     * 每次下载记录交付（业务编号用产线前缀）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public ReportFile report(Long id) {
        DatasetEntity ds = load(id);
        require("published".equals(ds.getStatus()), "仅已发布数据集可下载质量报告");
        TaskMainEntity task = ds.getTaskId() == null ? null : taskMapper.selectOneById(ds.getTaskId());

        List<ReviewOrderEntity> orders = reviewOrderMapper.selectListByQuery(QueryWrapper.create()
                .where("task_id = ?", ds.getTaskId()));
        long open = orders.stream()
                .filter(o -> "pending".equals(o.getStatus()) || "doing".equals(o.getStatus())).count();
        long closed = orders.stream().filter(o -> "done".equals(o.getStatus())).count();

        // 作废单（重跑产生）不计入复核处置；A/B/C 按有效复核单的条目统计。
        List<Long> effectiveOrderIds = orders.stream()
                .filter(o -> !"void".equals(o.getStatus()))
                .map(ReviewOrderEntity::getId).toList();
        long confirmed = 0;
        long revised = 0;
        long excluded = 0;
        if (!effectiveOrderIds.isEmpty()) {
            List<ReviewItemEntity> items = reviewItemMapper.selectListByQuery(QueryWrapper.create()
                            .where("task_id = ?", ds.getTaskId())).stream()
                    .filter(i -> effectiveOrderIds.contains(i.getOrderId())).toList();
            confirmed = items.stream().filter(i -> "A".equals(i.getConclusion())).count();
            revised = items.stream().filter(i -> "B".equals(i.getConclusion())).count();
            excluded = items.stream().filter(i -> "C".equals(i.getConclusion())).count();
        }

        int contentCount = ds.getItemCount() == null ? 0 : ds.getItemCount();
        int cCount = ds.getSkipCount() == null ? 0 : ds.getSkipCount();
        String lineName = LineRegistry.LINE_NAMES.getOrDefault(ds.getLine(), ds.getLine());
        String taskText = task == null ? "-" : task.getBizNo() + " " + task.getName();
        String publishTime = ds.getPublishTime() == null ? "-" : ds.getPublishTime().format(MINUTE);
        LocalDateTime generatedAt = LocalDateTime.now();
        String now = generatedAt.format(MINUTE);
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
        String stamp = generatedAt.format(STAMP);
        String filename = ds.getBizNo() + "_质量报告_" + stamp + ".txt";
        DeliveryLogEntity logRow = new DeliveryLogEntity();
        String prefix = LineRegistry.LINE_PREFIX.get(ds.getLine());
        logRow.setBizNo(BizId.nextUnique(prefix, candidate -> deliveryLogMapper.selectCountByQuery(
                QueryWrapper.create().where("biz_no = ?", candidate)) > 0));
        logRow.setDatasetId(id);
        logRow.setType("质量报告TXT");
        logRow.setFilename(filename);
        logRow.setOperator(AuthContext.username());
        deliveryLogMapper.insert(logRow);
        log.info("质量报告下载: dataset={} content={} A/B/C={}/{}/{} by={}", ds.getBizNo(),
                contentCount, confirmed, revised, excluded, AuthContext.username());
        return new ReportFile(filename, text.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * 质量版本说明：V1 直出、V2 复核闭环、V3 起重跑。
     */
    private String qualityVersionText(String semVer, long closed,
                                      long confirmed, long revised, long excluded) {
        int major = 1;
        if (semVer != null && semVer.matches("V\\d+\\.0")) {
            major = Integer.parseInt(semVer.substring(1, semVer.indexOf('.')));
        }
        List<String> factors = new ArrayList<>();
        if (major >= 3) {
            factors.add("成片错误重跑（第" + (major - 2) + "次）产出");
        }
        if (closed > 0) {
            factors.add("经条件复核闭环：确认" + confirmed + " / 修正" + revised + " / 跳过" + excluded);
        }
        if (factors.isEmpty()) {
            factors.add("产线直出");
        }
        return semVer + "（" + String.join("；", factors) + "）";
    }

    /**
     * 交付记录分页。
     */
    @Override
    public PageResult<DatasetDeliveryRowVO> deliveries(DeliveryListDTO dto) {
        QueryWrapper qw = QueryWrapper.create().orderBy("id desc");
        Page<DeliveryLogEntity> page = deliveryLogMapper.paginate(PageUtils.getPage(dto), qw);
        return PageUtils.getPageResult(page.map(logRow -> {
            DatasetDeliveryRowVO row = new DatasetDeliveryRowVO();
            row.setBizNo(logRow.getBizNo());
            row.setDatasetId(logRow.getDatasetId());
            DatasetEntity dataset = logRow.getDatasetId() == null
                    ? null : datasetMapper.selectOneById(logRow.getDatasetId());
            row.setDatasetBizNo(dataset == null ? null : dataset.getBizNo());
            row.setLineName(dataset == null ? null : LineRegistry.LINE_NAMES.get(dataset.getLine()));
            row.setType(logRow.getType());
            row.setFilename(logRow.getFilename());
            row.setOperator(logRow.getOperator());
            row.setTime(Times.text(logRow.getCreateTime()));
            return row;
        }));
    }

    private DatasetEntity load(Long id) {
        DatasetEntity dataset = datasetMapper.selectOneById(id);
        if (dataset == null) {
            throw new BizException("数据集不存在");
        }
        return dataset;
    }

    /**
     * 任务最近一次成功的环节执行记录；tag 为 null 时不限算子。
     */
    private TaskStageRunEntity latestDoneRun(Long taskId, String tag) {
        QueryWrapper qw = QueryWrapper.create()
                .where("task_id = ?", taskId)
                .and("status = ?", "done");
        if (tag != null) {
            qw.and("operator_tag = ?", tag);
        }
        return stageRunMapper.selectOneByQuery(qw.orderBy("id desc").limit(1));
    }

    // ==================== 视图 ====================

    private DatasetVO toVO(DatasetEntity dataset) {
        DatasetVO vo = BeanCopyUtils.copy(dataset, DatasetVO.class);
        vo.setLineName(LineRegistry.LINE_NAMES.get(dataset.getLine()));
        vo.setStatusName(STATUS_NAMES.get(dataset.getStatus()));
        vo.setPublishTime(Times.text(dataset.getPublishTime()));
        vo.setCreateTime(Times.text(dataset.getCreateTime()));
        return vo;
    }

    private DatasetDetailVO.Item itemVO(DatasetItemEntity item) {
        DatasetDetailVO.Item vo = new DatasetDetailVO.Item();
        vo.setId(item.getId());
        vo.setItemKey(item.getItemKey());
        vo.setPayload(item.getPayload() == null || item.getPayload().isBlank()
                ? null : JsonUtils.jsonToMap(item.getPayload()));
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
