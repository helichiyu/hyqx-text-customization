package com.hsmty.tcs.config;

import com.hsmty.core.common.web.ApiPrefixRegister;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * <p>文本定制化生产模块 API 前缀声明。
 *
 * <p>注册后 {@code com.hsmty.tcs.controller} 下的 Controller 统一挂载 {@code /tcs} 前缀，
 * 最终访问路径为 {@code /hs-api/tcs/**}。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Configuration
public class TcsApiPrefixConfiguration {

    @Bean
    public ApiPrefixRegister tcsApiPrefixRegister() {
        return new ApiPrefixRegister() {

            @Override
            public String module() {
                return "tcs";
            }

            @Override
            public String prefix() {
                return "/tcs";
            }

            @Override
            public String[] basePackages() {
                return new String[]{"com.hsmty.tcs.controller"};
            }
        };
    }
}
