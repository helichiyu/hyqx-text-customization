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
import com.hsmty.tcs.mapper.ReviewItemMapper;
import com.hsmty.tcs.mapper.ReviewOrderMapper;
import com.hsmty.tcs.mapper.TaskMainMapper;
import com.hsmty.tcs.mapper.TaskStageRunMapper;
import com.hsmty.tcs.operator.LineRegistry;
import com.hsmty.tcs.pojo.dto.ReviewListDTO;
import com.hsmty.tcs.pojo.po.DatasetEntity;
import com.hsmty.tcs.pojo.po.DatasetItemEntity;
import com.hsmty.tcs.pojo.po.ReviewItemEntity;
import com.hsmty.tcs.pojo.po.ReviewOrderEntity;
import com.hsmty.tcs.pojo.po.TaskMainEntity;
import com.hsmty.tcs.pojo.po.TaskStageRunEntity;
import com.hsmty.tcs.pojo.vo.ReviewAddResultVO;
import com.hsmty.tcs.pojo.vo.ReviewDetailVO;
import com.hsmty.tcs.pojo.vo.ReviewItemVO;
import com.hsmty.tcs.pojo.vo.ReviewOrderVO;
import com.hsmty.tcs.service.ReviewService;
import com.mybatisflex.core.paginate.Page;
import com.mybatisflex.core.query.QueryWrapper;
import com.mybatisflex.spring.service.impl.ServiceImpl;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * <p>条件复核：条目结论（A 确认 / B 修正 / C 剔除，B 保留改前改后值）、
 * 整单闭环（闭环后回写数据集行与任务状态）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReviewServiceImpl extends ServiceImpl<ReviewOrderMapper, ReviewOrderEntity>
        implements ReviewService {

    private final ReviewOrderMapper orderMapper;

    private final ReviewItemMapper itemMapper;

    private final TaskMainMapper taskMapper;

    private final DatasetMapper datasetMapper;

    private final DatasetItemMapper datasetItemMapper;

    private final TaskStageRunMapper stageRunMapper;

    @Override
    public Long resolveId(String reference) {
        String ref = reference == null ? "" : reference.trim();
        if (ref.matches("\\d+")) {
            try {
                return Long.valueOf(ref);
            } catch (NumberFormatException e) {
                throw new BizException("复核单引用格式错误", e);
            }
        }
        ReviewOrderEntity order = orderMapper.selectOneByQuery(QueryWrapper.create()
                .where("biz_no = ?", ref));
        if (order == null) {
            throw new BizException("复核单不存在");
        }
        return order.getId();
    }

    // ==================== 查询 ====================

    @Override
    public PageResult<ReviewOrderVO> page(ReviewListDTO dto) {
        QueryWrapper qw = QueryWrapper.create();
        if (dto.getStatus() != null && !dto.getStatus().isBlank()) {
            qw.and("status = ?", dto.getStatus());
        }
        if (dto.getLine() != null && !dto.getLine().isBlank()) {
            qw.and("line = ?", dto.getLine());
        }
        if (dto.getTaskId() != null) {
            qw.and("task_id = ?", dto.getTaskId());
        }
        qw.orderBy("create_time desc");
        Page<ReviewOrderEntity> page = orderMapper.paginate(PageUtils.getPage(dto), qw);
        return PageUtils.getPageResult(page.map(this::toVO));
    }

    /**
     * 复核单详情（含条目清单与来源执行记录）。
     */
    @Override
    public ReviewDetailVO detail(Long orderId) {
        ReviewOrderEntity order = load(orderId);
        ReviewOrderVO orderVO = toVO(order);
        TaskMainEntity sourceTask = taskMapper.selectOneById(order.getTaskId());
        orderVO.setTaskBizNo(sourceTask == null ? null : sourceTask.getBizNo());
        ReviewDetailVO detail = BeanCopyUtils.copy(orderVO, ReviewDetailVO.class);
        detail.setItems(itemMapper.selectListByQuery(QueryWrapper.create()
                        .where("order_id = ?", orderId).orderBy("id asc")).stream()
                .map(this::itemVO).toList());
        TaskStageRunEntity sourceRun = stageRunMapper.selectOneByQuery(QueryWrapper.create()
                .where("task_id = ?", order.getTaskId())
                .and("stage_name = ?", order.getStageName())
                .and("status = ?", "done")
                .orderBy("id desc").limit(1));
        detail.setRunId(sourceRun == null ? null : sourceRun.getId());
        detail.setImageRunId(sourceRun == null ? null : sourceRun.getId());
        return detail;
    }

    // ==================== 人工加入复核 ====================

    /**
     * 数据集明细「加入复核任务」：把一条数据集行加入本任务未闭环的复核单；
     * 无未闭环单时新建（触发码 manual_added）。仅候选数据集可加，已归集任务不可加。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public ReviewAddResultVO addFromDatasetItem(Long datasetItemId) {
        DatasetItemEntity item = datasetItemMapper.selectOneById(datasetItemId);
        if (item == null) {
            throw new BizException("数据集条目不存在");
        }
        DatasetEntity dataset = datasetMapper.selectOneById(item.getDatasetId());
        if (dataset == null || !"candidate".equals(dataset.getStatus())) {
            throw new BizException("仅候选数据集可加入复核");
        }
        TaskMainEntity task = taskMapper.selectOneById(item.getTaskId());
        if (task == null) {
            throw new BizException("来源任务不存在");
        }
        if ("collected".equals(task.getStatus())) {
            throw new BizException("任务已归集，不能再加入复核");
        }

        ReviewOrderEntity order = orderMapper.selectOneByQuery(QueryWrapper.create()
                .where("task_id = ?", task.getId())
                .and("status in (?, ?)", "pending", "doing")
                .orderBy("id desc").limit(1));
        if (order == null) {
            order = new ReviewOrderEntity();
            order.setBizNo(BizId.nextUnique("CR", candidate -> orderMapper.selectCountByQuery(
                    QueryWrapper.create().where("biz_no = ?", candidate)) > 0));
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
                .where("order_id = ?", order.getId())
                .and("item_key = ?", item.getItemKey()));
        if (exists != null && exists > 0) {
            // 重复加入按幂等处理：直接返回当前复核单，前端可安全重试。
            return new ReviewAddResultVO(order.getId(), order.getBizNo());
        }

        ReviewItemEntity ri = new ReviewItemEntity();
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
        return new ReviewAddResultVO(order.getId(), order.getBizNo());
    }

    // ==================== 结论与闭环 ====================

    /**
     * 条目结论：A 确认 / B 修正（必填修正后行，记录改前改后值）/ C 剔除。
     * 保存不闭环；首次结论后复核单转「复核中」。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void conclude(Long itemId, String conclusion, Map<String, Object> revisedPayload) {
        ReviewItemEntity item = itemMapper.selectOneById(itemId);
        if (item == null) {
            throw new BizException("复核条目不存在");
        }
        ReviewOrderEntity order = load(item.getOrderId());
        if ("void".equals(order.getStatus()) || "done".equals(order.getStatus())) {
            throw new BizException("复核单已" + ORDER_STATUS_NAMES.get(order.getStatus()) + "，不能再出结论");
        }
        String revisedJson = null;
        String beforeJson = null;
        String afterJson = null;
        switch (conclusion == null ? "" : conclusion) {
            case "A", "C" -> {
            }
            case "B" -> {
                require(revisedPayload != null && !revisedPayload.isEmpty(), "B 修正必须提交修正后的内容");
                Map<String, Object> before = item.getPayload() == null || item.getPayload().isBlank()
                        ? new LinkedHashMap<>() : JsonUtils.jsonToMap(item.getPayload());
                Map<String, Object> diffBefore = new LinkedHashMap<>();
                Map<String, Object> diffAfter = new LinkedHashMap<>();
                for (Map.Entry<String, Object> e : revisedPayload.entrySet()) {
                    Object old = before.get(e.getKey());
                    if (e.getValue() == null ? old != null : !e.getValue().equals(old)) {
                        diffBefore.put(e.getKey(), old);
                        diffAfter.put(e.getKey(), e.getValue());
                    }
                }
                require(!diffAfter.isEmpty(), "修正内容与原值一致，无需修正");
                Map<String, Object> merged = new LinkedHashMap<>(before);
                merged.putAll(revisedPayload);
                revisedJson = JsonUtils.toJsonString(merged);
                beforeJson = JsonUtils.toJsonString(diffBefore);
                afterJson = JsonUtils.toJsonString(diffAfter);
            }
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

    /**
     * 撤销条目结论（未闭环前）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void unconclude(Long itemId) {
        ReviewItemEntity item = itemMapper.selectOneById(itemId);
        if (item == null) {
            throw new BizException("复核条目不存在");
        }
        ReviewOrderEntity order = load(item.getOrderId());
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
                .where("order_id = ?", order.getId())
                .and("conclusion is not null"));
        if (left == 0 && "doing".equals(order.getStatus())) {
            order.setStatus("pending");
            orderMapper.update(order);
        }
    }

    /**
     * 整单闭环：要求全部条目已有结论；回写数据集行（A/B/C），重算条数；
     * 若任务处于待复核且所有复核单已闭环 → 任务转待归集。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void close(Long orderId) {
        ReviewOrderEntity order = load(orderId);
        require(!"done".equals(order.getStatus()), "复核单已闭环");
        require(!"void".equals(order.getStatus()), "复核单已作废");
        List<ReviewItemEntity> items = itemMapper.selectListByQuery(QueryWrapper.create()
                .where("order_id = ?", orderId));
        long unconcluded = items.stream().filter(i -> i.getConclusion() == null).count();
        require(unconcluded == 0, "还有 " + unconcluded + " 条条目未出结论，不能闭环");

        syncDatasetItems(order, items);

        order.setStatus("done");
        order.setCloseBy(AuthContext.username());
        order.setCloseTime(LocalDateTime.now());
        orderMapper.update(order);

        // 任务下无未闭环复核单 → 待复核转待归集
        Long open = orderMapper.selectCountByQuery(QueryWrapper.create()
                .where("task_id = ?", order.getTaskId())
                .and("status in (?, ?)", "pending", "doing"));
        if (open == 0) {
            TaskMainEntity task = taskMapper.selectOneById(order.getTaskId());
            if (task != null && "waitreview".equals(task.getStatus())) {
                task.setStatus("quality");
                taskMapper.update(task);
            }
        }
        log.info("复核单闭环: order={} items={} by={}", order.getBizNo(), items.size(),
                AuthContext.username());
    }

    /**
     * 删除复核单（逻辑删除，级联删除条目）；删除后任务下已无未闭环复核单时，
     * 待复核任务转为待归集。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void remove(Long orderId) {
        ReviewOrderEntity order = load(orderId);
        itemMapper.deleteByQuery(QueryWrapper.create().where("order_id = ?", orderId));
        orderMapper.deleteById(orderId);

        Long open = orderMapper.selectCountByQuery(QueryWrapper.create()
                .where("task_id = ?", order.getTaskId())
                .and("status in (?, ?)", "pending", "doing"));
        if (open == 0) {
            TaskMainEntity task = taskMapper.selectOneById(order.getTaskId());
            if (task != null && "waitreview".equals(task.getStatus())) {
                task.setStatus("quality");
                taskMapper.update(task);
            }
        }
        log.info("复核单删除: order={} by={}", order.getBizNo(), AuthContext.username());
    }

    /**
     * 闭环回写：A 已确认 / B 已修正（payload 换修正值）/ C 已剔除；重算数据集条数。
     */
    private void syncDatasetItems(ReviewOrderEntity order, List<ReviewItemEntity> items) {
        DatasetEntity dataset = datasetMapper.selectOneByQuery(QueryWrapper.create()
                .where("task_id = ?", order.getTaskId())
                .orderBy("id desc").limit(1));
        if (dataset == null) {
            log.warn("闭环时找不到任务数据集: task={}", order.getTaskId());
            return;
        }
        int excluded = 0;
        for (ReviewItemEntity ri : items) {
            List<DatasetItemEntity> targets = datasetItemMapper.selectListByQuery(QueryWrapper.create()
                    .where("dataset_id = ?", dataset.getId())
                    .and("item_key = ?", ri.getItemKey()));
            for (DatasetItemEntity di : targets) {
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
                .where("dataset_id = ?", dataset.getId())
                .and("review_status <> ?", "已剔除C"));
        dataset.setItemCount(valid == null ? 0 : valid.intValue());
        dataset.setSkipCount(excluded);
        datasetMapper.update(dataset);
    }

    private ReviewOrderEntity load(Long id) {
        ReviewOrderEntity order = orderMapper.selectOneById(id);
        if (order == null) {
            throw new BizException("复核单不存在");
        }
        return order;
    }

    // ==================== 视图 ====================

    private ReviewOrderVO toVO(ReviewOrderEntity order) {
        ReviewOrderVO vo = BeanCopyUtils.copy(order, ReviewOrderVO.class);
        vo.setLineName(LineRegistry.LINE_NAMES.get(order.getLine()));
        vo.setStatusName(ORDER_STATUS_NAMES.get(order.getStatus()));
        vo.setCreateTime(Times.text(order.getCreateTime()));
        vo.setCloseTime(Times.text(order.getCloseTime()));
        return vo;
    }

    private ReviewItemVO itemVO(ReviewItemEntity item) {
        ReviewItemVO vo = BeanCopyUtils.copy(item, ReviewItemVO.class);
        vo.setPayload(item.getPayload() == null || item.getPayload().isBlank()
                ? null : JsonUtils.jsonToMap(item.getPayload()));
        vo.setBeforeValue(item.getBeforeValue() == null || item.getBeforeValue().isBlank()
                ? null : JsonUtils.jsonToMap(item.getBeforeValue()));
        vo.setAfterValue(item.getAfterValue() == null || item.getAfterValue().isBlank()
                ? null : JsonUtils.jsonToMap(item.getAfterValue()));
        vo.setConcludeTime(Times.text(item.getConcludeTime()));
        return vo;
    }

    private void require(boolean cond, String msg) {
        if (!cond) {
            throw new BizException(msg);
        }
    }
}
