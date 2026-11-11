package com.hsmty.tcs.operator;

import com.hsmty.tcs.common.BizException;
import com.hsmty.tcs.config.TcsOperatorProperties;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * <p>产线注册表：四条产线的环节、算子链与参数映射（编排唯一事实来源）。
 *
 * <p>算子链顺序与《前后端对接说明》§5 一致；stage 区间用于把算子完成映射到环节①②③进度。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Component
public class LineRegistry {

    /**
     * 产线代码 → 中文名。
     */
    public static final Map<String, String> LINE_NAMES = Map.of(
            "formula", "公式文本",
            "layout", "复杂版面",
            "graphic", "图文融合",
            "metadata", "文本元信息");

    /**
     * 产线代码 → 业务编号前缀。
     */
    public static final Map<String, String> LINE_PREFIX = Map.of(
            "formula", "GS",
            "layout", "FZ",
            "graphic", "TW",
            "metadata", "YX");

    /**
     * 图文融合任务大类（与算子 category 枚举一致）。
     */
    public static final List<String> IMAGE_CLASSES = List.of("几何", "统计", "表格", "示意");

    /**
     * 素材白名单（对齐文档 v2：按产线固定）。
     */
    public static final Map<String, List<String>> LINE_WHITELIST = Map.of(
            "formula", List.of("pdf", "zip"),
            "layout", List.of("pdf", "zip"),
            "graphic", List.of("jpg", "jpeg", "zip"),
            "metadata", List.of("html", "zip"));

    /**
     * 链中的一个算子节点（tag/起始环节/结束环节）。
     */
    public record Node(String tag, int fromStage, int toStage) {
    }

    /**
     * 产线算子链（顺序即编排顺序）。
     */
    public static final Map<String, List<Node>> CHAINS = Map.of(
            "metadata", List.of(
                    new Node("meta_clean_slice", 1, 1),
                    new Node("meta_genre_judge", 1, 1),
                    new Node("meta_fact_extract", 2, 2),
                    new Node("meta_field_fill", 3, 3)),
            "formula", List.of(
                    new Node("fml_formula_locate", 1, 1),
                    new Node("fml_formula_recognize", 2, 3)),
            "layout", List.of(
                    new Node("lay_page_render", 1, 1),
                    new Node("lay_page_detect", 2, 3)),
            "graphic", List.of(
                    new Node("img_region_locate", 1, 1),
                    new Node("img_type_classify", 1, 1),
                    new Node("img_struct_describe", 2, 3)));

    /**
     * 环节名（进度展示，与交付说明一致）。
     */
    public static final Map<String, List<String>> STAGE_NAMES = Map.of(
            "metadata", List.of("文档接入与切片", "事实抽取", "元信息补全"),
            "formula", List.of("素材接入与定位", "公式识别", "公式结构化标注"),
            "layout", List.of("文档接入与分页", "逐页检测", "质量校验"),
            "graphic", List.of("图片接入与判型", "要素与结构提取", "描述生成"));

    private final TcsOperatorProperties properties;

    public LineRegistry(TcsOperatorProperties properties) {
        this.properties = properties;
    }

    /**
     * <p>算子服务根地址，如 {@code http://127.0.0.1:6301}。
     *
     * @param tag 算子标识
     * @return 算子根地址
     */
    public String url(String tag) {
        String url = properties.baseUrlOf(tag);
        if (url.isEmpty()) {
            throw new BizException("未配置算子端口: " + tag);
        }
        return url;
    }

    /**
     * <p>末位算子 tag。
     *
     * @param line 产线代码
     * @return 末位算子标识
     */
    public static String lastTag(String line) {
        List<Node> chain = CHAINS.get(line);
        return chain.get(chain.size() - 1).tag();
    }
}
