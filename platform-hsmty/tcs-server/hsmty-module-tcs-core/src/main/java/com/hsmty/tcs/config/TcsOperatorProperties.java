package com.hsmty.tcs.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * <p>算法算子接入配置。
 *
 * <p>算子独立部署，不内嵌在本服务中。支持两种部署形态：
 * <ul>
 *     <li>{@code per-port}（默认）：一台算子宿主机 + 每个算子一个端口；</li>
 *     <li>{@code shared-port}：11 个算子合并为一个容器，共用一个端口，按 {@code /<算子名>} 路径区分。</li>
 * </ul>
 * 其他配置不变，新增算子时仍在 {@code tcs.operator.ports} 中追加；未登记的算子调用时返回空地址，
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
     * 部署形态：{@code per-port}（默认，每算子独立端口）或
     * {@code shared-port}（合并容器，单端口 + 算子路径前缀）。
     */
    private String deployment = "per-port";

    /**
     * 合并容器部署时的公共端口（仅 {@code deployment=shared-port} 生效）。
     */
    private Integer sharedPort;

    /**
     * 算子名到端口的映射，算子名与 operators/ 目录下的服务名一致。
     */
    private Map<String, Integer> ports = new LinkedHashMap<>();

    /**
     * 算子产物文件读取方式：{@code http}（默认，经算子文件接口读取）或 {@code local}（本地联调，
     * 平台与算子共用挂载目录时直接读运行时目录）。
     */
    private String fileMode = "http";

    /**
     * 本地模式下的算子运行时根目录（仅 {@code fileMode=local} 生效）。
     */
    private String runtimeDir = "./op-runtime";

    /**
     * <p>拼接指定算子的访问基地址。
     *
     * @param operator 算子名，如 {@code meta_clean_slice}
     * @return {@code per-port} 形态返回 {@code http://127.0.0.1:6301}；
     *         {@code shared-port} 形态返回 {@code http://127.0.0.1:17022/meta_clean_slice}；
     *         算子未登记或公共端口未配置时返回空字符串
     */
    public String baseUrlOf(String operator) {
        if (ports.get(operator) == null) {
            return "";
        }
        String normalized = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        if ("shared-port".equalsIgnoreCase(deployment)) {
            if (sharedPort == null) {
                return "";
            }
            return normalized + ":" + sharedPort + "/" + operator;
        }
        return normalized + ":" + ports.get(operator);
    }
}
