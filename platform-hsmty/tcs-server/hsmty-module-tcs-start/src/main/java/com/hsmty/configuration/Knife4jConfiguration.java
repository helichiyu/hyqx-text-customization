package com.hsmty.configuration;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * <p>OpenAPI / Knife4j 文档配置。
 *
 * <p>登录态由 UAP/SSO Cookie 承载（见技术选型文档 §5.2，明确不引入 JWT/BCrypt），
 * 因此这里不声明 Bearer 安全方案，联调时以浏览器携带的 SSO Cookie 为准。
 * 生产环境通过 {@code springdoc.api-docs.enabled=false}、{@code springdoc.swagger-ui.enabled=false} 关闭入口。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Configuration
@ConditionalOnClass(name = "org.springdoc.webmvc.ui.SwaggerWelcomeWebMvc")
public class Knife4jConfiguration {

    /**
     * <p>构建平台 OpenAPI 元信息。
     *
     * @return OpenAPI 定义
     */
    @Bean
    public OpenAPI tcsOpenApi() {
        return new OpenAPI().info(new Info()
                .title("文本定制化生产平台 API")
                .description("HSMTY 2.0.1 基线；统一上下文 /hs-api，模块前缀 /tcs")
                .version("2.0.1"));
    }
}
