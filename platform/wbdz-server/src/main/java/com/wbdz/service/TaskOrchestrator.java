package com.wbdz.service;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.common.BizException;
import com.wbdz.common.BizId;
import com.wbdz.common.JsonUtil;
import com.wbdz.entity.Dataset;
import com.wbdz.entity.DatasetItem;
import com.wbdz.entity.MatBatch;
import com.wbdz.entity.MatFile;
import com.wbdz.entity.ReviewItem;
import com.wbdz.entity.ReviewOrder;
import com.wbdz.entity.TaskMain;
import com.wbdz.entity.TaskStageRun;
import com.wbdz.mapper.DatasetItemMapper;
import com.wbdz.mapper.DatasetMapper;
import com.wbdz.mapper.MatBatchMapper;
import com.wbdz.mapper.MatFileMapper;
import com.wbdz.mapper.ReviewItemMapper;
import com.wbdz.mapper.ReviewOrderMapper;
import com.wbdz.mapper.TaskMainMapper;
import com.wbdz.mapper.TaskStageRunMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static com.wbdz.entity.table.DatasetTableDef.DATASET;
import static com.wbdz.entity.table.MatFileTableDef.MAT_FILE;
import static com.wbdz.entity.table.ReviewOrderTableDef.REVIEW_ORDER;
import static com.wbdz.entity.table.TaskMainTableDef.TASK_MAIN;
import static com.wbdz.entity.table.TaskStageRunTableDef.TASK_STAGE_RUN;

/**
 * 任务编排：素材打包 → uploadFile → 顺序 predict（inputFile 原样透传、末位收口）
 * → 阶段 zip 消费（records→数据集、review→复核单）→ 状态流转 → removeFile 清理。
 *
 * <p>失败重试：每跳最多 3 次尝试（5s/15s 退避）；耗尽后任务回到 pending（可重跑/驳回）。
 * 重跑入口 runFrom：从指定环节起，以上一环节已 done 的 outputPath 续链。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class TaskOrchestrator {

    private final TaskMainMapper taskMapper;

    private final TaskStageRunMapper stageRunMapper;

    private final MatBatchMapper batchMapper;

    private final MatFileMapper fileMapper;

    private final ReviewOrderMapper reviewOrderMapper;

    private final ReviewItemMapper reviewItemMapper;

    private final DatasetMapper datasetMapper;

    private final DatasetItemMapper datasetItemMapper;

    private final OperatorClient operatorClient;

    @Value("${wbdz.storage-dir}")
    private String storageDir;

    /** 算子可接受的 predict 参数（对接说明 §8；快照中文名 → API 参数名）。 */
    private static final Map<String, List<String>> TAG_PARAMS = Map.ofEntries(
            Map.entry("meta_clean_slice", List.of()),
            Map.entry("meta_genre_judge", List.of("confidence_threshold", "concurrency")),
            Map.entry("meta_fact_extract", List.of("confidence_threshold", "concurrency")),
            Map.entry("meta_field_fill", List.of("confidence_threshold", "max_text_chars", "concurrency")),
            Map.entry("lay_page_render", List.of("dpi", "image_format")),
            Map.entry("lay_page_detect", List.of("confidence_threshold", "iou_threshold", "concurrency", "draw_overlay")),
            Map.entry("fml_formula_locate", List.of("dpi", "max_context_chars", "concurrency")),
            Map.entry("fml_formula_recognize", List.of("confidence_threshold", "concurrency")),
            Map.entry("img_region_locate", List.of("border_tolerance", "min_crop_size")),
            Map.entry("img_type_classify", List.of("category", "confidence_threshold", "concurrency")),
            Map.entry("img_struct_describe", List.of("confidence_threshold", "concurrency")));

    /** 快照参数中文名 → 算子参数名（名中空格忽略）。 */
    private static final Map<String, String> PARAM_NAME_MAP = Map.of(
            "并发数", "concurrency",
            "渲染DPI", "dpi",
            "渲染dpi", "dpi");

    /** 数据集行主键字段（按产线行形态优先级）。 */
    private static final List<String> KEY_FIELDS = List.of("instanceId", "pageId", "imageId", "docId", "id", "key");

    /** 正在执行的任务（防重复启动）。 */
    private final Set<Long> running = ConcurrentHashMap.newKeySet();

    /** 异步执行整链（虚拟线程）。 */
    public void startAsync(Long taskId, int fromStage) {
        if (!running.add(taskId)) {
            throw new BizException("任务正在执行中，请勿重复启动");
        }
        Thread.ofVirtual().name("wbdz-task-" + taskId).start(() -> {
            try {
                run(taskId, fromStage);
            } catch (Exception e) {
                log.error("任务执行异常: taskId={}", taskId, e);
                safeStatus(taskId, "pending");
            } finally {
                running.remove(taskId);
            }
        });
    }

    public boolean isRunning(Long taskId) {
        return running.contains(taskId);
    }

    // ==================== 主流程 ====================

    private void run(Long taskId, int fromStage) {
        TaskMain task = taskMapper.selectOneById(taskId);
        if (task == null) {
            log.error("任务不存在: {}", taskId);
            return;
        }
        safeStatus(taskId, "processing");
        // 重跑：作废未闭环复核单（已闭环的保留）
        voidOpenOrders(taskId);

        List<LineRegistry.Node> all = LineRegistry.CHAINS.get(task.getLine());
        List<LineRegistry.Node> nodes = all.stream().filter(n -> n.fromStage() >= fromStage).toList();
        if (nodes.isEmpty()) {
            nodes = all;
        }
        String uniqueId = task.getId() + "_" + task.getBatchId();

        // 起点输入：环节 1 上传素材 zip；否则用上一环节已 done 的输出目录续链
        String carryInput = null;
        if (fromStage <= 1) {
            byte[] zip = zipBatchFiles(task.getBatchId());
            operatorClient.uploadFile(nodes.get(0).tag(), uniqueId, zip);
        } else {
            carryInput = resumeInput(all, nodes.get(0), taskId);
            if (carryInput == null) {
                log.warn("找不到环节 {} 之前的成功输出，回退整链重跑: taskId={}", fromStage, taskId);
                byte[] zip = zipBatchFiles(task.getBatchId());
                operatorClient.uploadFile(all.get(0).tag(), uniqueId, zip);
                nodes = all;
            }
        }

        String prevOutput = carryInput;
        for (int i = 0; i < nodes.size(); i++) {
            LineRegistry.Node node = nodes.get(i);
            boolean last = node.tag().equals(LineRegistry.lastTag(task.getLine()));
            Map<String, Object> body = buildBody(task, node, i == 0 && prevOutput == null, prevOutput, last);
            Map<String, Object> data = predictWithRetry(task, node, body);
            prevOutput = String.valueOf(data.get("outputFile"));
            updateProgress(task, node, data);
        }

        consumeStageOutput(task, prevOutput);
        cleanup(task, all.get(0).tag(), uniqueId);
    }

    /** 构造 predict 请求体。 */
    private Map<String, Object> buildBody(TaskMain task, LineRegistry.Node node,
                                          boolean stageFirst, String inputFile, boolean last) {
        Map<String, Object> body = new LinkedHashMap<String, Object>();
        if (stageFirst) {
            body.put("uniqueId", task.getId() + "_" + task.getBatchId());
        } else {
            body.put("inputFile", inputFile);
        }
        if (last) {
            body.put("isLastOperator", true);
        }
        // 图文线判型必带大类
        if ("img_type_classify".equals(node.tag())) {
            body.put("category", task.getImageClass());
        }
        // 快照参数 + 任务级阈值透传（只传该算子认识的键）
        Map<String, String> snapshot = snapshotMap(task);
        List<String> accepts = TAG_PARAMS.getOrDefault(node.tag(), List.of());
        for (Map.Entry<String, String> e : snapshot.entrySet()) {
            String apiName = PARAM_NAME_MAP.get(e.getKey().replace(" ", ""));
            if (apiName != null && accepts.contains(apiName)) {
                body.put(apiName, parseValue(apiName, e.getValue()));
            }
        }
        if (accepts.contains("confidence_threshold") && task.getThreshold() != null) {
            body.put("confidence_threshold", task.getThreshold());
        }
        return body;
    }

    /** 区间值（如 4-8）取下界；数值型参数转数字，其余原样。 */
    private static Object parseValue(String apiName, String raw) {
        String v = raw.trim();
        if (v.matches("\\d+-\\d+")) {
            v = v.substring(0, v.indexOf('-'));
        }
        if ("concurrency".equals(apiName) || "dpi".equals(apiName) || "max_text_chars".equals(apiName)
                || "max_context_chars".equals(apiName) || "border_tolerance".equals(apiName)
                || "min_crop_size".equals(apiName)) {
            return Integer.parseInt(v);
        }
        return v;
    }

    private Map<String, String> snapshotMap(TaskMain task) {
        Map<String, String> m = new LinkedHashMap<String, String>();
        if (task.getParamSnapshot() != null) {
            for (Map<String, Object> g : JsonUtil.readList(task.getParamSnapshot())) {
                m.put(String.valueOf(g.get("name")), String.valueOf(g.get("value")));
            }
        }
        return m;
    }

    /** 单跳 predict：最多 3 次尝试，每次尝试一条 stage_run 记录。 */
    private Map<String, Object> predictWithRetry(TaskMain task, LineRegistry.Node node, Map<String, Object> body) {
        int maxAttempts = 3;
        long[] backoff = {5000, 15000};
        BizException lastError = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            TaskStageRun run = newRunRow(task, node, attempt);
            try {
                Map<String, Object> data = operatorClient.predict(node.tag(), body);
                run.setStatus("done");
                run.setSummary(data.get("summary") == null ? null : JsonUtil.write(data.get("summary")));
                run.setSkipped(data.get("skipped") == null ? "[]" : JsonUtil.write(data.get("skipped")));
                run.setFailed(data.get("failed") == null ? "[]" : JsonUtil.write(data.get("failed")));
                run.setOutputPath(String.valueOf(data.get("outputFile")));
                run.setEndTime(LocalDateTime.now());
                stageRunMapper.update(run);
                return data;
            } catch (BizException e) {
                lastError = e;
                run.setStatus("error");
                run.setFailed(JsonUtil.write(List.of(Map.of("attempt", attempt, "error", safeMsg(e)))));
                run.setEndTime(LocalDateTime.now());
                stageRunMapper.update(run);
                log.warn("predict 失败: task={} tag={} attempt={}/{} err={}",
                        task.getId(), node.tag(), attempt, maxAttempts, e.getMessage());
                if (attempt < maxAttempts) {
                    try {
                        Thread.sleep(backoff[attempt - 1]);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }
        throw lastError == null ? new BizException("算子执行失败") : lastError;
    }

    private TaskStageRun newRunRow(TaskMain task, LineRegistry.Node node, int attempt) {
        Long prior = stageRunMapper.selectCountByQuery(QueryWrapper.create()
                .where(TASK_STAGE_RUN.TASK_ID.eq(task.getId()))
                .and(TASK_STAGE_RUN.OPERATOR_TAG.eq(node.tag())));
        TaskStageRun run = new TaskStageRun();
        run.setTaskId(task.getId());
        run.setStageNo(node.fromStage());
        run.setStageName(LineRegistry.STAGE_NAMES.get(task.getLine()).get(node.fromStage() - 1));
        run.setOperatorTag(node.tag());
        run.setStatus("running");
        run.setAttempt(prior.intValue() + attempt);
        run.setStartTime(LocalDateTime.now());
        stageRunMapper.insert(run);
        return run;
    }

    /** 进度：环节完成即推进 currentStage。 */
    private void updateProgress(TaskMain task, LineRegistry.Node node, Map<String, Object> data) {
        TaskMain t = taskMapper.selectOneById(task.getId());
        if (t != null) {
            int stage = Math.max(t.getCurrentStage() == null ? 0 : t.getCurrentStage(), node.toStage());
            t.setCurrentStage(stage);
            taskMapper.update(t);
        }
    }

    /** 续链输入：起点前一跳最近一次 done 的输出。 */
    private String resumeInput(List<LineRegistry.Node> all, LineRegistry.Node startNode, Long taskId) {
        int startIdx = all.indexOf(startNode);
        for (int i = startIdx - 1; i >= 0; i--) {
            TaskStageRun prev = stageRunMapper.selectOneByQuery(QueryWrapper.create()
                    .where(TASK_STAGE_RUN.TASK_ID.eq(taskId))
                    .and(TASK_STAGE_RUN.OPERATOR_TAG.eq(all.get(i).tag()))
                    .and(TASK_STAGE_RUN.STATUS.eq("done"))
                    .orderBy(TASK_STAGE_RUN.ID.desc()).limit(1));
            if (prev != null && prev.getOutputPath() != null) {
                return prev.getOutputPath();
            }
        }
        return null;
    }

    // ==================== 阶段产物消费 ====================

    /**
     * 末位 stage zip：records.jsonl → 数据集（candidate）+ 明细行；review → 复核单；
     * 空成果（全失败/全跳过）不建数据集，任务回 pending。
     */
    private void consumeStageOutput(TaskMain task, String stageOutputFile) {
        Path zipPath = operatorClient.toHostPath(stageOutputFile);
        Map<String, List<Map<String, Object>>> parsed = readStageZip(zipPath);
        List<Map<String, Object>> records = parsed.getOrDefault("records", List.of());
        List<Map<String, Object>> reviewRows = parsed.getOrDefault("review", List.of());

        if (records.isEmpty()) {
            log.warn("阶段产物无 records 行（全失败/全跳过）: taskId={} zip={}", task.getId(), zipPath);
            safeStatus(task.getId(), "pending");
            return;
        }

        // review 集合 = 末位 review.jsonl ∪ 行内标记待复核（中段环节透传下来的）
        Map<String, Map<String, Object>> reviewByKey = new LinkedHashMap<String, Map<String, Object>>();
        for (Map<String, Object> row : reviewRows) {
            reviewByKey.put(itemKey(row), row);
        }
        for (Map<String, Object> row : records) {
            if ("待复核".equals(row.get("reviewStatus"))) {
                reviewByKey.putIfAbsent(itemKey(row), row);
            }
        }

        Dataset ds = newDataset(task, records.size(), !reviewByKey.isEmpty());
        List<DatasetItem> items = new ArrayList<>(records.size());
        for (Map<String, Object> row : records) {
            DatasetItem item = new DatasetItem();
            item.setDatasetId(ds.getId());
            item.setTaskId(task.getId());
            item.setItemKey(itemKey(row));
            item.setPayload(JsonUtil.write(row));
            boolean wait = reviewByKey.containsKey(item.getItemKey());
            item.setReviewStatus(wait ? "待复核" : "未进入复核");
            item.setRevisionStatus(wait ? "未修正" : "-");
            item.setConfidence(minConfidence(row));
            items.add(item);
            datasetItemMapper.insert(item);
        }
        ds.setItemCount(items.size());
        ds.setSkipCount(0);
        datasetMapper.update(ds);

        if (!reviewByKey.isEmpty()) {
            createReviewOrder(task, reviewByKey);
        }
        safeStatus(task.getId(), reviewByKey.isEmpty() ? "quality" : "waitreview");
        log.info("阶段产物消费完成: task={} dataset={} items={} review={}",
                task.getId(), ds.getBizNo(), items.size(), reviewByKey.size());
    }

    private Dataset newDataset(TaskMain task, int itemCount, boolean hadReview) {
        Long prior = datasetMapper.selectCountByQuery(QueryWrapper.create()
                .where(DATASET.TASK_ID.eq(task.getId())));
        int base = hadReview ? 2 : 1;
        Dataset ds = new Dataset();
        ds.setBizNo(BizId.next("DS"));
        ds.setLine(task.getLine());
        ds.setTaskId(task.getId());
        ds.setItemCount(itemCount);
        ds.setSkipCount(0);
        ds.setSemVer("V" + (base + prior) + ".0");
        ds.setStatus("candidate");
        ds.setCreateBy("system");
        datasetMapper.insert(ds);
        return ds;
    }

    /** 一轮一条复核单；触发码取行内 code（算子侧补码改造前用 reviewReason 兜底）。 */
    private void createReviewOrder(TaskMain task, Map<String, Map<String, Object>> rowsByKey) {
        List<String> codes = new ArrayList<>();
        List<String> reasons = new ArrayList<>();
        for (Map<String, Object> row : rowsByKey.values()) {
            String code = row.get("code") == null ? null : String.valueOf(row.get("code"));
            String reason = row.get("reviewReason") == null ? "行标记待复核" : String.valueOf(row.get("reviewReason"));
            if (code != null && !codes.contains(code)) {
                codes.add(code);
            }
            if (!reasons.contains(reason)) {
                reasons.add(reason);
            }
        }
        List<String> stageNames = LineRegistry.STAGE_NAMES.get(task.getLine());
        ReviewOrder order = new ReviewOrder();
        order.setBizNo(BizId.next("CR"));
        order.setTaskId(task.getId());
        order.setLine(task.getLine());
        order.setStageName(stageNames.get(stageNames.size() - 1));
        order.setTriggerCode(String.join(",", codes.isEmpty() ? List.of("review") : codes));
        order.setTriggerDesc(String.join("；", reasons));
        order.setItemCount(rowsByKey.size());
        order.setStatus("pending");
        order.setCreateBy("system");
        reviewOrderMapper.insert(order);

        for (Map.Entry<String, Map<String, Object>> e : rowsByKey.entrySet()) {
            ReviewItem item = new ReviewItem();
            item.setOrderId(order.getId());
            item.setTaskId(task.getId());
            item.setItemKey(e.getKey());
            item.setCode(e.getValue().get("code") == null ? "review" : String.valueOf(e.getValue().get("code")));
            item.setReason(e.getValue().get("reviewReason") == null ? "行标记待复核"
                    : String.valueOf(e.getValue().get("reviewReason")));
            item.setPayload(JsonUtil.write(e.getValue()));
            reviewItemMapper.insert(item);
        }
        log.info("生成复核单: task={} order={} items={}", task.getId(), order.getBizNo(), rowsByKey.size());
    }

    /** 解包阶段 zip：records.jsonl / review.jsonl（取最短匹配的条目，兼容目录包裹）。 */
    private Map<String, List<Map<String, Object>>> readStageZip(Path zipPath) {
        Map<String, List<Map<String, Object>>> out = new LinkedHashMap<String, List<Map<String, Object>>>();
        out.put("records", new ArrayList<>());
        out.put("review", new ArrayList<>());
        try (ZipInputStream zin = new ZipInputStream(
                new ByteArrayInputStream(Files.readAllBytes(zipPath)), StandardCharsets.UTF_8)) {
            ZipEntry entry;
            while ((entry = zin.getNextEntry()) != null) {
                if (entry.isDirectory()) {
                    continue;
                }
                String name = entry.getName().replace("\\", "/");
                boolean isRecord = name.endsWith("/records.jsonl") || name.equals("records.jsonl");
                boolean isReview = name.endsWith("/review.jsonl") || name.equals("review.jsonl");
                if (!isRecord && !isReview) {
                    continue;
                }
                String text = new String(zin.readAllBytes(), StandardCharsets.UTF_8);
                for (String line : text.split("\n")) {
                    if (line.isBlank()) {
                        continue;
                    }
                    try {
                        (isRecord ? out.get("records") : out.get("review")).add(JsonUtil.readMap(line));
                    } catch (Exception e) {
                        log.warn("jsonl 行解析失败（跳过）: {} => {}", name, safeCut(line));
                    }
                }
            }
        } catch (Exception e) {
            throw new BizException("阶段产物读取失败: " + zipPath + " - " + e.getMessage());
        }
        return out;
    }

    // ==================== 工具 ====================

    /** 批次有效文件打 zip（内存；上传给阶段首算子）。 */
    private byte[] zipBatchFiles(Long batchId) {
        MatBatch batch = batchMapper.selectOneById(batchId);
        if (batch == null) {
            throw new BizException("素材批次不存在");
        }
        List<MatFile> files = fileMapper.selectListByQuery(QueryWrapper.create()
                .where(MAT_FILE.BATCH_ID.eq(batchId)).and(MAT_FILE.STATUS.eq("passed")));
        if (files.isEmpty()) {
            throw new BizException("批次内没有有效素材");
        }
        try (ByteArrayOutputStream buf = new ByteArrayOutputStream();
             var zout = new java.util.zip.ZipOutputStream(buf, StandardCharsets.UTF_8)) {
            Set<String> used = new HashSet<>();
            for (MatFile f : files) {
                String entryName = f.getName();
                int i = 1;
                while (!used.add(entryName)) {
                    entryName = "(" + i++ + ")" + f.getName();
                }
                zout.putNextEntry(new ZipEntry(entryName));
                zout.write(Files.readAllBytes(Path.of(storageDir, f.getStorePath())));
                zout.closeEntry();
            }
            zout.finish();
            return buf.toByteArray();
        } catch (IOException e) {
            throw new BizException("素材打包失败: " + e.getMessage());
        }
    }

    /** 行主键：instanceId/pageId/imageId/docId 优先，兜底序号。 */
    public static String itemKey(Map<String, Object> row) {
        for (String k : KEY_FIELDS) {
            if (row.get(k) != null && !String.valueOf(row.get(k)).isBlank()) {
                return String.valueOf(row.get(k));
            }
        }
        return "row-" + Integer.toHexString(row.hashCode());
    }

    /** 行级最低置信度：递归收集 key 含 confidence 的数值取最小。 */
    public static BigDecimal minConfidence(Object node) {
        BigDecimal min = null;
        if (node instanceof Map<?, ?> m) {
            for (Map.Entry<?, ?> e : m.entrySet()) {
                String key = String.valueOf(e.getKey()).toLowerCase();
                // 只认置信度字段本身；lowConfidenceCount / lowConfidenceReasons 不是分数。
                boolean confKey = (key.equals("confidence") || key.endsWith("_confidence")
                        || key.endsWith("conf"))
                        && !key.contains("count") && !key.contains("reason");
                if (confKey) {
                    BigDecimal v = numeric(e.getValue());
                    if (v != null && (min == null || v.compareTo(min) < 0)) {
                        min = v;
                    }
                    if (e.getValue() instanceof Map<?, ?> sub) {
                        for (Object sv : sub.values()) {
                            BigDecimal n = numeric(sv);
                            if (n != null && (min == null || n.compareTo(min) < 0)) {
                                min = n;
                            }
                        }
                    }
                } else {
                    BigDecimal v = minConfidence(e.getValue());
                    if (v != null && (min == null || v.compareTo(min) < 0)) {
                        min = v;
                    }
                }
            }
        } else if (node instanceof List<?> l) {
            for (Object o : l) {
                BigDecimal v = minConfidence(o);
                if (v != null && (min == null || v.compareTo(min) < 0)) {
                    min = v;
                }
            }
        }
        return min;
    }

    private static BigDecimal numeric(Object v) {
        if (v instanceof Number n) {
            return new BigDecimal(n.toString());
        }
        if (v instanceof String s && s.matches("\\d+(\\.\\d+)?")) {
            return new BigDecimal(s);
        }
        return null;
    }

    private void voidOpenOrders(Long taskId) {
        List<ReviewOrder> open = reviewOrderMapper.selectListByQuery(QueryWrapper.create()
                .where(REVIEW_ORDER.TASK_ID.eq(taskId))
                .and(REVIEW_ORDER.STATUS.in("pending", "doing")));
        for (ReviewOrder o : open) {
            o.setStatus("void");
            reviewOrderMapper.update(o);
        }
    }

    private void cleanup(TaskMain task, String firstTag, String uniqueId) {
        try {
            operatorClient.removeFile(firstTag, uniqueId);
        } catch (Exception e) {
            log.warn("任务收尾清理失败（不影响结果）: taskId={} {}", task.getId(), e.getMessage());
        }
    }

    private void safeStatus(Long taskId, String status) {
        try {
            TaskMain t = taskMapper.selectOneById(taskId);
            if (t != null) {
                t.setStatus(status);
                taskMapper.update(t);
            }
        } catch (Exception e) {
            log.error("更新任务状态失败: taskId={} status={}", taskId, status, e);
        }
    }

    private static String safeMsg(Exception e) {
        String m = e.getMessage();
        return m == null ? e.getClass().getSimpleName() : (m.length() > 400 ? m.substring(0, 400) : m);
    }

    private static String safeCut(String s) {
        return s.length() > 120 ? s.substring(0, 120) + "..." : s;
    }
}
