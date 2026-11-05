package com.wbdz.service;

import com.wbdz.common.BizException;
import com.wbdz.common.JsonUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;

/**
 * 算子服务 HTTP 客户端（/healthz、/uploadFile、/removeFile、/predict）。
 *
 * <p>约定见《前后端对接说明》：predict 为长任务（超时 1800s）；业务失败 HTTP 仍 200，按 code 分流；
 * inputFile 只接受算子 OUTPUT_DIR/INPUT_DIR 之内路径，编排侧原样透传。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Slf4j
@Component
public class OperatorClient {

    private final LineRegistry lineRegistry;

    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15))
            .build();

    @Value("${wbdz.op-runtime-dir}")
    private String opRuntimeDir;

    public OperatorClient(LineRegistry lineRegistry) {
        this.lineRegistry = lineRegistry;
    }

    /** 算子是否健康。 */
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

    /** 上传素材 zip（uniqueId=任务id_批次id；重传同名清空旧素材）。 */
    public void uploadFile(String tag, String uniqueId, byte[] zipBytes) {
        String boundary = "wbdz-" + java.util.UUID.randomUUID();
        byte[] body = multipart(boundary, "file", "batch_" + uniqueId + ".zip", zipBytes);
        HttpResponse<String> resp = send(tag, HttpRequest.newBuilder()
                        .uri(URI.create(lineRegistry.url(tag) + "/uploadFile?uniqueId=" + uniqueId))
                        .timeout(Duration.ofSeconds(300))
                        .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                        .POST(HttpRequest.BodyPublishers.ofByteArrays(java.util.List.of(body))),
                "uploadFile");
        requireOk(tag, resp, "uploadFile");
    }

    /** 清理素材（幂等）。 */
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
     * 调用 predict。
     *
     * @param body 请求体：uniqueId（阶段首）/ inputFile（中段，原样透传）/ isLastOperator / 算子参数
     * @return data 对象（outputFile、lineageFile、summary、skipped、failed）
     */
    public Map<String, Object> predict(String tag, Map<String, Object> body) {
        HttpResponse<String> resp = send(tag, HttpRequest.newBuilder()
                        .uri(URI.create(lineRegistry.url(tag) + "/predict"))
                        .timeout(Duration.ofSeconds(1800))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(JsonUtil.write(body),
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

    /** 读取指定 stage_run 的样本级进度；进度尚未生成时返回 null。 */
    public Map<String, Object> readProgress(Long runId) {
        if (runId == null) {
            return null;
        }
        java.nio.file.Path runtimeRoot = java.nio.file.Path.of(opRuntimeDir);
        for (String outputDir : new String[]{"outputs", "output"}) {
            java.nio.file.Path path = runtimeRoot.resolve(outputDir)
                    .resolve("_progress").resolve(runId + ".json");
            if (!java.nio.file.Files.isRegularFile(path)) {
                continue;
            }
            try {
                return JsonUtil.readMap(java.nio.file.Files.readString(path, StandardCharsets.UTF_8));
            } catch (Exception e) {
                log.warn("读取算子进度失败: runId={} path={} err={}", runId, path, e.getMessage(), e);
            }
        }
        return null;
    }
    /**
     * 算子返回路径 → 平台宿主机路径。
     *
     * <p>部署形态（compose）下算子回 `/data/...`，按挂载根映射到宿主机 op-runtime；
     * 本地进程直跑时算子在 Windows 上回 `E:\data\...` 形式的绝对路径，只要落在
     * op-runtime 根之下同样放行。两种形态都做闸门校验，闸外路径一律拒绝。
     */
    public java.nio.file.Path toHostPath(String containerPath) {
        String p = containerPath == null ? "" : containerPath.replace("\\", "/");
        java.nio.file.Path runtimeRoot = java.nio.file.Path.of(opRuntimeDir).toAbsolutePath().normalize();
        if (p.startsWith("/data/")) {
            return runtimeRoot.resolve(p.substring("/data/".length()));
        }
        java.nio.file.Path host = java.nio.file.Path.of(p).toAbsolutePath().normalize();
        if (host.startsWith(runtimeRoot)) {
            return host;
        }
        throw new BizException("算子返回了闸外路径（仅支持 /data/ 或 op-runtime 之内）: " + containerPath);
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
            Map<String, Object> envelope = JsonUtil.readMap(resp.body());
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

    /** 构造 multipart/form-data 单文件请求体。 */
    private static byte[] multipart(String boundary, String field, String filename, byte[] file) {
        var out = new java.io.ByteArrayOutputStream();
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
