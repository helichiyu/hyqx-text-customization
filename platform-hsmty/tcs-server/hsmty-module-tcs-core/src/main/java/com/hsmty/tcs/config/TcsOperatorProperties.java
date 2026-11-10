package com.hsmty.tcs.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * <p>算法算子接入配置。
 *
 * <p>算子独立部署，不内嵌在本服务中；部署形态是"一台算子宿主机 + 每个算子一个端口"，
 * 因此配置为统一基地址加算子端口表，而不是给每个算子写一条完整 URL。
 * 新增算子时在 {@code tcs.operator.ports} 中追加即可，未登记的算子调用时返回空地址，
 * 由调用方按"空地址不阻塞启动、调用失败返回稳定业务错误"处理。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Data
@ConfigurationProperties(prefix = "tcs.operator")
public class TcsOperatorProperties {

    /**
     * 算子宿主机基地址，不含端口，例如 http://127.0.0.1。
     */
    private String baseUrl = "http://127.0.0.1";

    /**
     * 算子名到端口的映射，算子名与 operators/ 目录下的服务名一致。
     */
    private Map<String, Integer> ports = new LinkedHashMap<>();

    /**
     * <p>拼接指定算子的访问基地址。
     *
     * @param operator 算子名，如 {@code meta_clean_slice}
     * @return 形如 {@code http://127.0.0.1:6301}；算子未登记时返回空字符串
     */
    public String baseUrlOf(String operator) {
        Integer port = ports.get(operator);
        if (port == null) {
            return "";
        }
        String normalized = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        return normalized + ":" + port;
    }
}
