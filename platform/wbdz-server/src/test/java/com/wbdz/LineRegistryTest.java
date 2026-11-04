package com.wbdz;

import com.wbdz.service.LineRegistry;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 产线注册表与《前后端对接说明》§5 编排顺序、《素材管理·研发对齐 v2》白名单一致。
 *
 * @author wbdz
 * @since 2026-11-03
 */
class LineRegistryTest {

    @Test
    void chainsMatchSpecOrder() {
        assertThat(tags("metadata")).containsExactly(
                "meta_clean_slice", "meta_genre_judge", "meta_fact_extract", "meta_field_fill");
        assertThat(tags("formula")).containsExactly("fml_formula_locate", "fml_formula_recognize");
        assertThat(tags("layout")).containsExactly("lay_page_render", "lay_page_detect");
        assertThat(tags("graphic")).containsExactly(
                "img_region_locate", "img_type_classify", "img_struct_describe");
    }

    @Test
    void lastOperatorIsChainTail() {
        assertThat(LineRegistry.lastTag("metadata")).isEqualTo("meta_field_fill");
        assertThat(LineRegistry.lastTag("formula")).isEqualTo("fml_formula_recognize");
        assertThat(LineRegistry.lastTag("layout")).isEqualTo("lay_page_detect");
        assertThat(LineRegistry.lastTag("graphic")).isEqualTo("img_struct_describe");
    }

    @Test
    void stageMappingCoversOneToThree() {
        LineRegistry.CHAINS.forEach((line, nodes) -> {
            int min = nodes.stream().mapToInt(LineRegistry.Node::fromStage).min().orElse(0);
            int max = nodes.stream().mapToInt(LineRegistry.Node::toStage).max().orElse(0);
            assertThat(min).as("%s 起始环节", line).isEqualTo(1);
            assertThat(max).as("%s 结束环节", line).isEqualTo(3);
            assertThat(LineRegistry.STAGE_NAMES.get(line)).as("%s 环节名", line).hasSize(3);
        });
    }

    @Test
    void whitelistMatchesAlignmentV2() {
        assertThat(LineRegistry.LINE_WHITELIST.get("formula")).containsExactly("pdf", "zip");
        assertThat(LineRegistry.LINE_WHITELIST.get("layout")).containsExactly("pdf", "zip");
        assertThat(LineRegistry.LINE_WHITELIST.get("graphic")).containsExactly("jpg", "jpeg", "zip");
        assertThat(LineRegistry.LINE_WHITELIST.get("metadata")).containsExactly("html", "zip");
    }

    @Test
    void graphicImageClassesMatchOperatorEnum() {
        assertThat(LineRegistry.IMAGE_CLASSES).containsExactly("几何", "统计", "表格", "示意");
    }

    private List<String> tags(String line) {
        return LineRegistry.CHAINS.get(line).stream().map(LineRegistry.Node::tag).toList();
    }
}
