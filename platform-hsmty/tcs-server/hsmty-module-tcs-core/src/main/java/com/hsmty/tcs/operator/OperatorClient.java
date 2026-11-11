package com.hsmty.tcs.operator;

import com.hsmty.core.util.JsonUtils;
import com.hsmty.tcs.common.BizException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * <p>算子服务 HTTP 客户端（/healthz、/uploadFile、/removeFile、/predict）。
 *
 * <p>约定见《前后端对接说明》：predict 为长任务（超时 1800s）；业务失败 HTTP 仍 200，按 code 分流；
 * inputFile 只接受算子 OUTPUT_DIR/INPUT_DIR 之内路径，编排侧原样透传。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Slf4j
@Component
public class OperatorClient {

    private final LineRegistry lineRegistry;

    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15))
            .build();

    public OperatorClient(LineRegistry lineRegistry) {
        this.lineRegistry = lineRegistry;
    }

    /**
     * <p>算子是否健康。
     *
     * @param tag 算子标识
     * @return 健康返回 true
     */
    public boolean healthz(String tag) {
        try {
            HttpResponse<String> resp = http.send(HttpRequest.newBuilder()
                            .uri(URI.create(lineRegistry.url(tag) + "/healthz"))
                            .timeout(Duration.ofSeconds(5))
                            .GET().build(),
                    HttpResponse.BodyHandlers.ofString());
            return resp.statusCode() == 200;
        } catch (Exception e) {
            log.warn("算子健康检查失败: tag={} err={}", tag, e.getMessage(), e);
            return false;
        }
    }

    /**
     * <p>上传素材 zip（uniqueId=任务id_批次id；重传同名清空旧素材）。
     *
     * @param tag      算子标识
     * @param uniqueId 任务与批次的唯一标识
     * @param zipBytes 素材压缩包
     */
    public void uploadFile(String tag, String uniqueId, byte[] zipBytes) {
        String boundary = "tcs-" + UUID.randomUUID();
        byte[] body = multipart(boundary, "file", "batch_" + uniqueId + ".zip", zipBytes);
        HttpResponse<String> resp = send(tag, HttpRequest.newBuilder()
                        .uri(URI.create(lineRegistry.url(tag) + "/uploadFile?uniqueId=" + uniqueId))
                        .timeout(Duration.ofSeconds(300))
                        .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                        .POST(HttpRequest.BodyPublishers.ofByteArrays(List.of(body))),
                "uploadFile");
        requireOk(tag, resp, "uploadFile");
    }

    /**
     * <p>清理素材（幂等）。
     *
     * @param tag      算子标识
     * @param uniqueId 任务与批次的唯一标识
     */
    public void removeFile(String tag, String uniqueId) {
        try {
            HttpResponse<String> resp = send(tag, HttpRequest.newBuilder()
                            .uri(URI.create(lineRegistry.url(tag) + "/removeFile?uniqueId=" + uniqueId))
                            .timeout(Duration.ofSeconds(60))
                            .POST(HttpRequest.BodyPublishers.noBody()),
                    "removeFile");
            requireOk(tag, resp, "removeFile");
        } catch (Exception e) {
            log.warn("removeFile 失败（幂等可重试）: tag={} err={}", tag, e.getMessage(), e);
        }
    }

    /**
     * <p>调用 predict。
     *
     * @param tag  算子标识
     * @param body 请求体：uniqueId（阶段首）/ inputFile（中段，原样透传）/ isLastOperator / 算子参数
     * @return data 对象（outputFile、lineageFile、summary、skipped、failed）
     */
    public Map<String, Object> predict(String tag, Map<String, Object> body) {
        HttpResponse<String> resp = send(tag, HttpRequest.newBuilder()
                        .uri(URI.create(lineRegistry.url(tag) + "/predict"))
                        .timeout(Duration.ofSeconds(1800))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(JsonUtils.toJsonString(body),
                                StandardCharsets.UTF_8)),
                "predict");
        Map<String, Object> envelope = parseEnvelope(tag, resp, "predict");
        Object data = envelope.get("data");
        if (data instanceof Map<?, ?> m) {
            @SuppressWarnings("unchecked")
            Map<String, Object> dataMap = (Map<String, Object>) m;
            return dataMap;
        }
        throw new BizException("算子[" + tag + "] predict 响应缺少 data");
    }

    // ==================== 内部 ====================

    private HttpResponse<String> send(String tag, HttpRequest.Builder builder, String action) {
        try {
            HttpResponse<String> resp = http.send(builder.build(), HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() >= 500) {
                throw new BizException("算子[" + tag + "] " + action + " 服务错误 HTTP " + resp.statusCode());
            }
            return resp;
        } catch (IOException | InterruptedException e) {
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new BizException("算子[" + tag + "] " + action + " 连接失败: " + e.getMessage(), e);
        }
    }

    private Map<String, Object> parseEnvelope(String tag, HttpResponse<String> resp, String action) {
        try {
            Map<String, Object> envelope = JsonUtils.jsonToMap(resp.body());
            int code = envelope.get("code") == null ? -1 : Integer.parseInt(String.valueOf(envelope.get("code")));
            if (code != 0) {
                // 业务失败 HTTP 仍 200，按 code 分流
                throw new BizException("算子[" + tag + "] " + action + " 业务失败: " + envelope.get("msg"));
            }
            return envelope;
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            throw new BizException("算子[" + tag + "] " + action + " 响应解析失败: " + resp.body(), e);
        }
    }

    private void requireOk(String tag, HttpResponse<String> resp, String action) {
        if (resp.statusCode() != 200) {
            throw new BizException("算子[" + tag + "] " + action + " HTTP " + resp.statusCode() + ": " + resp.body());
        }
        parseEnvelope(tag, resp, action);
    }

    /**
     * <p>构造 multipart/form-data 单文件请求体。
     */
    private static byte[] multipart(String boundary, String field, String filename, byte[] file) {
        var out = new ByteArrayOutputStream();
        try {
            byte[] head = ("--" + boundary + "\r\n"
                    + "Content-Disposition: form-data; name=\"" + field + "\"; filename=\"" + filename + "\"\r\n"
                    + "Content-Type: application/zip\r\n\r\n").getBytes(StandardCharsets.UTF_8);
            out.write(head);
            out.write(file);
            out.write(("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
            return out.toByteArray();
        } catch (IOException e) {
            throw new BizException("构造上传请求失败", e);
        }
    }
}
