package com.wbdz.common;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Map;

/**
 * JSON 帮助类（统一 ObjectMapper）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
public final class JsonUtil {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonUtil() {
    }

    public static String write(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new BizException("JSON 序列化失败", e);
        }
    }

    public static <T> T read(String json, Class<T> type) {
        try {
            return MAPPER.readValue(json, type);
        } catch (Exception e) {
            throw new BizException("JSON 解析失败", e);
        }
    }

    public static JsonNode tree(String json) {
        try {
            return MAPPER.readTree(json);
        } catch (Exception e) {
            throw new BizException("JSON 解析失败", e);
        }
    }

    public static List<Map<String, Object>> readList(String json) {
        try {
            return MAPPER.readValue(json, new TypeReference<>() {
            });
        } catch (Exception e) {
            throw new BizException("JSON 解析失败", e);
        }
    }

    public static Map<String, Object> readMap(String json) {
        try {
            return MAPPER.readValue(json, new TypeReference<>() {
            });
        } catch (Exception e) {
            throw new BizException("JSON 解析失败", e);
        }
    }

    public static ObjectMapper mapper() {
        return MAPPER;
    }
}
