package com.hsmty;

import com.hsmty.core.util.AppVersionUtils;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.autoconfigure.RefreshAutoConfiguration;
import org.springframework.cloud.client.discovery.simple.SimpleDiscoveryClientAutoConfiguration;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.EnableAspectJAutoProxy;

/**
 * <p>文本定制化生产平台启动类。
 *
 * <p>位于 {@code com.hsmty} 根包，保证组件扫描与 {@code @EnableFeignClients}
 * 覆盖 {@code com.hsmty.**}。按 HSMTY 基线排除服务发现与配置刷新自动装配，
 * Feign 地址只来自 {@code application.yml} 的显式配置项。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@SpringBootApplication(exclude = {SimpleDiscoveryClientAutoConfiguration.class, RefreshAutoConfiguration.class})
@EnableAspectJAutoProxy
@EnableFeignClients
public class RunApplication {

    public static void main(String[] args) {
        ConfigurableApplicationContext context = SpringApplication.run(RunApplication.class, args);
        String template = """
                ============================================================
                  文本定制化生产平台 · tcs  (v%s)
                  上下文 /hs-api   模块前缀 /tcs   文档 /hs-api/swagger-ui.html
                ============================================================
                """;
        String version = AppVersionUtils.resolve(context.getEnvironment().getProperty("app.version"), RunApplication.class);
        System.out.println(String.format(template, version));
    }

}
