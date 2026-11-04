package com.wbdz.service;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.common.AuthContext;
import com.wbdz.common.BizException;
import com.wbdz.common.BizId;
import com.wbdz.common.JsonUtil;
import com.wbdz.common.PageResult;
import com.wbdz.entity.Dataset;
import com.wbdz.entity.DatasetItem;
import com.wbdz.entity.ReviewItem;
import com.wbdz.entity.ReviewOrder;
import com.wbdz.entity.TaskMain;
import com.wbdz.mapper.DatasetItemMapper;
import com.wbdz.mapper.DatasetMapper;
import com.wbdz.mapper.ReviewItemMapper;
import com.wbdz.mapper.ReviewOrderMapper;
import com.wbdz.mapper.TaskMainMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static com.wbdz.entity.table.DatasetItemTableDef.DATASET_ITEM;
import static com.wbdz.entity.table.DatasetTableDef.DATASET;
import static com.wbdz.entity.table.ReviewItemTableDef.REVIEW_ITEM;
import static com.wbdz.entity.table.ReviewOrderTableDef.REVIEW_ORDER;

/**
 * 条件复核：条目结论（A 确认 / B 修正 / C 剔除，B 保留改前改后值）、
 * 整单闭环（闭环后回写数据集行与任务状态）、重跑作废由编排侧处理。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReviewService {

    /** 复核单状态中文名。 */
    public static final Map<String, String> ORDER_STATUS_NAMES = Map.of(
            "pending", "待复核", "doing", "复核中", "done", "已闭环", "void", "已作废");

    private final ReviewOrderMapper orderMapper;

    private final ReviewItemMapper itemMapper;

    private final TaskMainMapper taskMapper;

    private final DatasetMapper datasetMapper;

    private final DatasetItemMapper datasetItemMapper;

    // ==================== 查询 ====================

    public PageResult<Map<String, Object>> page(String status, String line, Long taskId,
                                                int pageNum, int pageSize) {
        QueryWrapper qw = QueryWrapper.create();
        if (status != null && !status.isBlank()) {
            qw.and(REVIEW_ORDER.STATUS.eq(status));
        }
        if (line != null && !line.isBlank()) {
            qw.and(REVIEW_ORDER.LINE.eq(line));
        }
        if (taskId != null) {
            qw.and(REVIEW_ORDER.TASK_ID.eq(taskId));
        }
        long total = orderMapper.selectCountByQuery(qw);
        List<ReviewOrder> rows = orderMapper.selectListByQuery(qw
                .orderBy(REVIEW_ORDER.CREATE_TIME.desc())
                .offset((long) (pageNum - 1) * pageSize).limit(pageSize));
        return PageResult.of(total, pageNum, pageSize,
                rows.stream().map(this::toView).toList());
    }

    /** 复核单详情（含条目清单与原始行）。 */
    public Map<String, Object> detail(Long orderId) {
        ReviewOrder order = load(orderId);
        Map<String, Object> m = toView(order);
        m.put("items", itemMapper.selectListByQuery(QueryWrapper.create()
                        .where(REVIEW_ITEM.ORDER_ID.eq(orderId)).orderBy(REVIEW_ITEM.ID.asc())).stream()
                .map(this::itemView).toList());
        return m;
    }

    // ==================== 人工加入复核 ====================

    /**
     * 数据集明细「加入复核任务」：把一条数据集行加入本任务未闭环的复核单；
     * 无未闭环单时新建（触发码 manual_added）。仅候选数据集可加，已归集任务不可加。
     */
    @Transactional(rollbackFor = Exception.class)
    public ReviewOrder addFromDatasetItem(Long datasetItemId) {
        DatasetItem item = datasetItemMapper.selectOneById(datasetItemId);
        if (item == null) {
            throw new BizException("数据集条目不存在");
        }
        Dataset dataset = datasetMapper.selectOneById(item.getDatasetId());
        if (dataset == null || !"candidate".equals(dataset.getStatus())) {
            throw new BizException("仅候选数据集可加入复核");
        }
        TaskMain task = taskMapper.selectOneById(item.getTaskId());
        if (task == null) {
            throw new BizException("来源任务不存在");
        }
        if ("collected".equals(task.getStatus())) {
            throw new BizException("任务已归集，不能再加入复核");
        }

        ReviewOrder order = orderMapper.selectOneByQuery(QueryWrapper.create()
                .where(REVIEW_ORDER.TASK_ID.eq(task.getId()))
                .and(REVIEW_ORDER.STATUS.in("pending", "doing"))
                .orderBy(REVIEW_ORDER.ID.desc()).limit(1));
        if (order == null) {
            order = new ReviewOrder();
            order.setBizNo(BizId.next("CR"));
            order.setTaskId(task.getId());
            order.setLine(task.getLine());
            order.setStageName("人工加入");
            order.setTriggerCode("manual_added");
            order.setTriggerDesc("数据集明细人工加入");
            order.setItemCount(0);
            order.setStatus("pending");
            order.setCreateBy(AuthContext.username());
            orderMapper.insert(order);
        }

        Long exists = itemMapper.selectCountByQuery(QueryWrapper.create()
                .where(REVIEW_ITEM.ORDER_ID.eq(order.getId()))
                .and(REVIEW_ITEM.ITEM_KEY.eq(item.getItemKey())));
        if (exists != null && exists > 0) {
            throw new BizException("该条目已在复核单中");
        }

        ReviewItem ri = new ReviewItem();
        ri.setOrderId(order.getId());
        ri.setTaskId(task.getId());
        ri.setItemKey(item.getItemKey());
        ri.setCode("manual_added");
        ri.setReason("数据集明细人工加入");
        ri.setPayload(item.getPayload());
        itemMapper.insert(ri);

        order.setItemCount((order.getItemCount() == null ? 0 : order.getItemCount()) + 1);
        // 已有条目未全部出结论时，人工加入不改变「复核中」状态
        if ("pending".equals(order.getStatus()) && order.getItemCount() > 1) {
            order.setStatus("doing");
        }
        orderMapper.update(order);

        item.setReviewStatus("待复核");
        item.setRevisionStatus("未修正");
        datasetItemMapper.update(item);

        if ("quality".equals(task.getStatus())) {
            task.setStatus("waitreview");
            taskMapper.update(task);
        }
        log.info("人工加入复核: order={} item={} by={}", order.getBizNo(), item.getItemKey(),
                AuthContext.username());
        return order;
    }

    // ==================== 结论与闭环 ====================

    /**
     * 条目结论：A 确认 / B 修正（必填修正后行，记录改前改后值）/ C 剔除。
     * 保存不闭环；首次结论后复核单转「复核中」。
     */
    @Transactional(rollbackFor = Exception.class)
    public void conclude(Long itemId, String conclusion, Map<String, Object> revisedPayload) {
        ReviewItem item = itemMapper.selectOneById(itemId);
        if (item == null) {
            throw new BizException("复核条目不存在");
        }
        ReviewOrder order = load(item.getOrderId());
        if ("void".equals(order.getStatus()) || "done".equals(order.getStatus())) {
            throw new BizException("复核单已" + ORDER_STATUS_NAMES.get(order.getStatus()) + "，不能再出结论");
        }
        String payloadJson;
        String revisedJson = null;
        String beforeJson = null;
        String afterJson = null;
        switch (conclusion == null ? "" : conclusion) {
            case "A" -> payloadJson = item.getPayload();
            case "B" -> {
                require(revisedPayload != null && !revisedPayload.isEmpty(), "B 修正必须提交修正后的内容");
                Map<String, Object> before = JsonUtil.readMap(item.getPayload());
                Map<String, Object> diffBefore = new LinkedHashMap<String, Object>();
                Map<String, Object> diffAfter = new LinkedHashMap<String, Object>();
                for (Map.Entry<String, Object> e : revisedPayload.entrySet()) {
                    Object old = before.get(e.getKey());
                    if (e.getValue() == null ? old != null : !e.getValue().equals(old)) {
                        diffBefore.put(e.getKey(), old);
                        diffAfter.put(e.getKey(), e.getValue());
                    }
                }
                require(!diffAfter.isEmpty(), "修正内容与原值一致，无需修正");
                Map<String, Object> merged = new LinkedHashMap<String, Object>(before);
                merged.putAll(revisedPayload);
                payloadJson = JsonUtil.write(merged);
                revisedJson = payloadJson;
                beforeJson = JsonUtil.write(diffBefore);
                afterJson = JsonUtil.write(diffAfter);
            }
            case "C" -> payloadJson = item.getPayload();
            default -> throw new BizException("结论取值：A 确认 / B 修正 / C 剔除");
        }
        item.setConclusion(conclusion);
        item.setRevisedPayload(revisedJson);
        item.setBeforeValue(beforeJson);
        item.setAfterValue(afterJson);
        item.setOperator(AuthContext.username());
        item.setConcludeTime(LocalDateTime.now());
        itemMapper.update(item);

        if ("pending".equals(order.getStatus())) {
            order.setStatus("doing");
            orderMapper.update(order);
        }
    }

    /** 撤销条目结论（未闭环前）。 */
    @Transactional(rollbackFor = Exception.class)
    public void unconclude(Long itemId) {
        ReviewItem item = itemMapper.selectOneById(itemId);
        if (item == null) {
            throw new BizException("复核条目不存在");
        }
        ReviewOrder order = load(item.getOrderId());
        require(!"done".equals(order.getStatus()) && !"void".equals(order.getStatus()),
                "复核单已闭环/作废，不能撤销");
        item.setConclusion(null);
        item.setRevisedPayload(null);
        item.setBeforeValue(null);
        item.setAfterValue(null);
        item.setOperator(null);
        item.setConcludeTime(null);
        itemMapper.update(item);
        Long left = itemMapper.selectCountByQuery(QueryWrapper.create()
                .where(REVIEW_ITEM.ORDER_ID.eq(order.getId()))
                .and(REVIEW_ITEM.CONCLUSION.isNotNull()));
        if (left == 0 && "doing".equals(order.getStatus())) {
            order.setStatus("pending");
            orderMapper.update(order);
        }
    }

    /**
     * 整单闭环：要求全部条目已有结论；回写数据集行（A/B/C），重算条数；
     * 若任务处于待复核且所有复核单已闭环 → 任务转待归集。
     */
    @Transactional(rollbackFor = Exception.class)
    public void close(Long orderId) {
        ReviewOrder order = load(orderId);
        require(!"done".equals(order.getStatus()), "复核单已闭环");
        require(!"void".equals(order.getStatus()), "复核单已作废");
        List<ReviewItem> items = itemMapper.selectListByQuery(QueryWrapper.create()
                .where(REVIEW_ITEM.ORDER_ID.eq(orderId)));
        long unconcluded = items.stream().filter(i -> i.getConclusion() == null).count();
        require(unconcluded == 0, "还有 " + unconcluded + " 条条目未出结论，不能闭环");

        syncDatasetItems(order, items);

        order.setStatus("done");
        order.setCloseBy(AuthContext.username());
        order.setCloseTime(LocalDateTime.now());
        orderMapper.update(order);

        // 任务下无未闭环复核单 → 待复核转待归集
        Long open = orderMapper.selectCountByQuery(QueryWrapper.create()
                .where(REVIEW_ORDER.TASK_ID.eq(order.getTaskId()))
                .and(REVIEW_ORDER.STATUS.in("pending", "doing")));
        if (open == 0) {
            TaskMain task = taskMapper.selectOneById(order.getTaskId());
            if (task != null && "waitreview".equals(task.getStatus())) {
                task.setStatus("quality");
                taskMapper.update(task);
            }
        }
        log.info("复核单闭环: order={} items={} by={}", order.getBizNo(), items.size(),
                AuthContext.username());
    }

    /** 闭环回写：A 已确认 / B 已修正（payload 换修正值）/ C 已剔除；重算数据集条数。 */
    private void syncDatasetItems(ReviewOrder order, List<ReviewItem> items) {
        Dataset dataset = datasetMapper.selectOneByQuery(QueryWrapper.create()
                .where(DATASET.TASK_ID.eq(order.getTaskId()))
                .orderBy(DATASET.ID.desc()).limit(1));
        if (dataset == null) {
            log.warn("闭环时找不到任务数据集: task={}", order.getTaskId());
            return;
        }
        int excluded = 0;
        for (ReviewItem ri : items) {
            List<DatasetItem> targets = datasetItemMapper.selectListByQuery(QueryWrapper.create()
                    .where(DATASET_ITEM.DATASET_ID.eq(dataset.getId()))
                    .and(DATASET_ITEM.ITEM_KEY.eq(ri.getItemKey())));
            for (DatasetItem di : targets) {
                switch (ri.getConclusion()) {
                    case "A" -> {
                        di.setReviewStatus("已确认A");
                        di.setRevisionStatus("-");
                    }
                    case "B" -> {
                        di.setReviewStatus("已修正B");
                        di.setRevisionStatus("已修正");
                        di.setPayload(ri.getRevisedPayload());
                    }
                    case "C" -> {
                        di.setReviewStatus("已剔除C");
                        di.setRevisionStatus("已剔除");
                        excluded++;
                    }
                    default -> {
                    }
                }
                datasetItemMapper.update(di);
            }
        }
        Long valid = datasetItemMapper.selectCountByQuery(QueryWrapper.create()
                .where(DATASET_ITEM.DATASET_ID.eq(dataset.getId()))
                .and(DATASET_ITEM.REVIEW_STATUS.ne("已剔除C")));
        dataset.setItemCount(valid.intValue());
        dataset.setSkipCount(excluded);
        datasetMapper.update(dataset);
    }

    // ==================== 视图 ====================

    private Map<String, Object> toView(ReviewOrder o) {
        Map<String, Object> m = new LinkedHashMap<String, Object>();
        m.put("id", o.getId());
        m.put("bizNo", o.getBizNo());
        m.put("taskId", o.getTaskId());
        m.put("line", o.getLine());
        m.put("lineName", LineRegistry.LINE_NAMES.get(o.getLine()));
        m.put("stageName", o.getStageName());
        m.put("triggerCode", o.getTriggerCode());
        m.put("triggerDesc", o.getTriggerDesc());
        m.put("itemCount", o.getItemCount());
        m.put("status", o.getStatus());
        m.put("statusName", ORDER_STATUS_NAMES.get(o.getStatus()));
        m.put("createTime", String.valueOf(o.getCreateTime()));
        m.put("closeBy", o.getCloseBy());
        m.put("closeTime", String.valueOf(o.getCloseTime()));
        return m;
    }

    private Map<String, Object> itemView(ReviewItem i) {
        Map<String, Object> m = new LinkedHashMap<String, Object>();
        m.put("id", i.getId());
        m.put("orderId", i.getOrderId());
        m.put("itemKey", i.getItemKey());
        m.put("code", i.getCode());
        m.put("reason", i.getReason());
        m.put("payload", i.getPayload() == null ? null : JsonUtil.readMap(i.getPayload()));
        m.put("conclusion", i.getConclusion());
        m.put("beforeValue", i.getBeforeValue() == null ? null : JsonUtil.readMap(i.getBeforeValue()));
        m.put("afterValue", i.getAfterValue() == null ? null : JsonUtil.readMap(i.getAfterValue()));
        m.put("operator", i.getOperator());
        m.put("concludeTime", String.valueOf(i.getConcludeTime()));
        return m;
    }

    private ReviewOrder load(Long id) {
        ReviewOrder o = orderMapper.selectOneById(id);
        if (o == null) {
            throw new BizException("复核单不存在");
        }
        return o;
    }

    private void require(boolean cond, String msg) {
        if (!cond) {
            throw new BizException(msg);
        }
    }
}
