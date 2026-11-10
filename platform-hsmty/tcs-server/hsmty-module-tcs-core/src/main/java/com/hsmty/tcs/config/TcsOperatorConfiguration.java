package com.hsmty.tcs.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * <p>算子接入配置注册。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Configuration
@EnableConfigurationProperties(TcsOperatorProperties.class)
public class TcsOperatorConfiguration {
}
