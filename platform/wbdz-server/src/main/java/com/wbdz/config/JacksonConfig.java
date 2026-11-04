package com.wbdz.config;

import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * JSON 序列化配置：雪花 ID（Long）统一输出字符串。
 *
 * <p>业务主键为 18 位雪花号，超出 JavaScript Number 安全整数范围（2^53−1），
 * 前端直接按数字解析会丢精度，导致「任务不存在 / 复核单不存在」。统一序列化为
 * 字符串后，前端按不透明 ID 使用；请求体里的字符串仍可正常绑定为 Long。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Configuration
public class JacksonConfig {

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer longToStringCustomizer() {
        return builder -> builder
                .serializerByType(Long.class, ToStringSerializer.instance)
                .serializerByType(Long.TYPE, ToStringSerializer.instance);
    }
}
