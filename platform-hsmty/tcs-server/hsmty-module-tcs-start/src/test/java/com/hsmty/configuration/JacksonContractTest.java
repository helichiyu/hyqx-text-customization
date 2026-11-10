package com.hsmty.configuration;

import com.hsmty.core.common.configuration.JacksonConfiguration;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * <p>JSON 序列化契约测试：验证框架自带的 Long 处理策略。
 *
 * <p>框架 {@code hsmty-common-core} 已注册 Long 序列化器：超出 JavaScript 安全整数范围
 * （±9007199254740991）的 Long 输出为字符串，范围内仍输出数字。
 * 本服务不再重复注册同名的 {@code JacksonConfiguration}，避免 Bean 名冲突，
 * 该测试用于锁定这一依赖行为，框架升级导致策略变化时能及时发现。
 *
 * @author helichiyu
 * @since 2.0.1
 */
class JacksonContractTest {

    @Test
    void shouldSerializeUnsafeLongAsStringAndSafeLongAsNumber() {
        JsonMapper.Builder builder = JsonMapper.builder();
        new JacksonConfiguration().szJacksonCustomizer().customize(builder);
        JsonMapper mapper = builder.build();

        String json = mapper.writeValueAsString(Map.of(
                "id", 1024000000000000001L,
                "count", 3L,
                "boundary", 9007199254740991L));

        assertThat(json).contains("\"id\":\"1024000000000000001\"");
        assertThat(json).contains("\"count\":3");
        assertThat(json).contains("\"boundary\":9007199254740991");
    }
}
