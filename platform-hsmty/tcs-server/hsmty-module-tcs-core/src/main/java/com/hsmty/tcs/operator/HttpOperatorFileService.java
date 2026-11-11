package com.hsmty.tcs.operator;

import com.hsmty.core.util.JsonUtils;
import com.hsmty.tcs.common.BizException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * <p>HTTP 模式产物读取：经算子接口远程读取产物，不依赖共享文件系统。
 *
 * <p>依赖算子侧实现以下接口（见 {@code docs/算子文件接口约定.md}）：
 * <ul>
 *     <li>{@code GET /listFiles?path=...} → {@code {code:0,data:[{name,size}]}}</li>
 *     <li>{@code GET /downloadFile?path=...&name=...} → 文件字节</li>
 *     <li>{@code GET /progress?runId=...} → {@code {code:0,data:{...}}}</li>
 * </ul>
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Slf4j
@Service
@ConditionalOnProperty(name = "tcs.operator.file-mode", havingValue = "http", matchIfMissing = true)
public class HttpOperatorFileService implements OperatorFileService {

    private final LineRegistry lineRegistry;

    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15))
            .build();

    public HttpOperatorFileService(LineRegistry lineRegistry) {
        this.lineRegistry = lineRegistry;
    }

    @Override
    public List<OperatorFile> list(String tag, String path) {
        if (path == null || path.isBlank()) {
            return List.of();
        }
        HttpResponse<String> resp = send(tag, HttpRequest.newBuilder()
                        .uri(URI.create(lineRegistry.url(tag) + "/listFiles?path=" + encode(path)))
                        .timeout(Duration.ofSeconds(120))
                        .GET(),
                "listFiles");
        Map<String, Object> envelope = parseEnvelope(tag, resp, "listFiles");
        Object data = envelope.get("data");
        if (!(data instanceof List<?> list)) {
            return List.of();
        }
        List<OperatorFile> out = new ArrayList<>(list.size());
        for (Object item : list) {
            if (item instanceof Map<?, ?> m) {
                Object name = m.get("name") == null ? m.get("path") : m.get("name");
                Object size = m.get("size");
                if (name != null) {
                    out.add(new OperatorFile(String.valueOf(name),
                            size instanceof Number n ? n.longValue() : parseLong(size)));
                }
            } else if (item != null) {
                out.add(new OperatorFile(String.valueOf(item), 0L));
            }
        }
        return out;
    }

    @Override
    public byte[] readEntry(String tag, String path, String name) {
        if (path == null || path.isBlank() || name == null || name.isBlank()) {
            throw new BizException("产物路径与条目名不能为空");
        }
        HttpResponse<byte[]> resp = sendBytes(tag, HttpRequest.newBuilder()
                        .uri(URI.create(lineRegistry.url(tag) + "/downloadFile?path=" + encode(path)
                                + "&name=" + encode(name)))
                        .timeout(Duration.ofSeconds(600))
                        .GET(),
                "downloadFile");
        if (resp.statusCode() != 200) {
            throw new BizException("算子[" + tag + "] downloadFile HTTP " + resp.statusCode()
                    + ": " + bodyText(resp.body()));
        }
        return resp.body();
    }

    @Override
    public Map<String, Object> progress(String tag, Long runId) {
        if (runId == null) {
            return null;
        }
        try {
            HttpResponse<String> resp = send(tag, HttpRequest.newBuilder()
                            .uri(URI.create(lineRegistry.url(tag) + "/progress?runId=" + runId))
                            .timeout(Duration.ofSeconds(10))
                            .GET(),
                    "progress");
            Map<String, Object> envelope = parseEnvelope(tag, resp, "progress");
            Object data = envelope.get("data");
            if (data instanceof Map<?, ?> m) {
                @SuppressWarnings("unchecked")
                Map<String, Object> map = (Map<String, Object>) m;
                return map;
            }
        } catch (Exception e) {
            log.debug("读取算子进度不可用: tag={} runId={} err={}", tag, runId, e.getMessage());
        }
        return null;
    }

    // ==================== 内部 ====================

    private HttpResponse<String> send(String tag, HttpRequest.Builder builder, String action) {
        try {
            return http.send(builder.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        } catch (IOException | InterruptedException e) {
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new BizException("算子[" + tag + "] " + action + " 连接失败: " + e.getMessage(), e);
        }
    }

    private HttpResponse<byte[]> sendBytes(String tag, HttpRequest.Builder builder, String action) {
        try {
            return http.send(builder.build(), HttpResponse.BodyHandlers.ofByteArray());
        } catch (IOException | InterruptedException e) {
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new BizException("算子[" + tag + "] " + action + " 连接失败: " + e.getMessage(), e);
        }
    }

    private Map<String, Object> parseEnvelope(String tag, HttpResponse<String> resp, String action) {
        if (resp.statusCode() != 200) {
            throw new BizException("算子[" + tag + "] " + action + " HTTP " + resp.statusCode());
        }
        try {
            Map<String, Object> envelope = JsonUtils.jsonToMap(resp.body());
            Object code = envelope.get("code");
            if (code == null || Integer.parseInt(String.valueOf(code)) != 0) {
                throw new BizException("算子[" + tag + "] " + action + " 业务失败: " + envelope.get("msg"));
            }
            return envelope;
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            throw new BizException("算子[" + tag + "] " + action + " 响应解析失败: " + resp.body(), e);
        }
    }

    private static String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    private static long parseLong(Object value) {
        try {
            return value == null ? 0L : Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException e) {
            return 0L;
        }
    }

    private static String bodyText(byte[] body) {
        if (body == null || body.length == 0) {
            return "";
        }
        String text = new String(body, StandardCharsets.UTF_8);
        return text.length() > 300 ? text.substring(0, 300) : text;
    }
}
