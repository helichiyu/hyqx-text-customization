package com.wbdz;

import com.wbdz.service.TaskOrchestrator;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 数据集行主键提取与行级最低置信度计算（纯函数部分）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
class TaskOrchestratorTest {

    @Test
    void itemKeyPrefersLineSpecificId() {
        // 公式行
        assertThat(TaskOrchestrator.itemKey(Map.of("instanceId", "inst-1", "docId", "d1")))
                .isEqualTo("inst-1");
        // 版面行
        assertThat(TaskOrchestrator.itemKey(Map.of("pageId", "doc1-#3", "docId", "doc1")))
                .isEqualTo("doc1-#3");
        // 图文行
        assertThat(TaskOrchestrator.itemKey(Map.of("imageId", "img_9"))).isEqualTo("img_9");
        // 元信息行
        assertThat(TaskOrchestrator.itemKey(Map.of("docId", "doc_abc"))).isEqualTo("doc_abc");
        // 兜底
        assertThat(TaskOrchestrator.itemKey(Map.of("foo", "bar"))).isNotBlank();
    }

    @Test
    void minConfidenceTakesLowestAcrossRow() {
        Map<String, Object> row = Map.of(
                "recognitionConfidence", 0.92,
                "semanticConfidence", 0.71,
                "nested", Map.of("confidence", Map.of("type", 0.99, "ocr", 0.65)),
                "list", List.of(Map.of("x", 1)));
        assertThat(TaskOrchestrator.minConfidence(row)).isEqualByComparingTo(new BigDecimal("0.65"));
    }

    @Test
    void minConfidenceNullWhenAbsent() {
        assertThat(TaskOrchestrator.minConfidence(Map.of("a", 1, "b", List.of("x")))).isNull();
    }

    @Test
    void minConfidenceIgnoresConfidenceCountAndReadsLayoutScores() {
        Map<String, Object> row = Map.of(
                "lowConfidenceCount", 0,
                "lowConfidenceReasons", "框选偏低",
                "elements", List.of(
                        Map.of("bboxConf", 0.95, "typeConf", 0.86),
                        Map.of("bboxConf", 0.90, "typeConf", 0.92)));
        assertThat(TaskOrchestrator.minConfidence(row)).isEqualByComparingTo(new BigDecimal("0.86"));
    }
}
