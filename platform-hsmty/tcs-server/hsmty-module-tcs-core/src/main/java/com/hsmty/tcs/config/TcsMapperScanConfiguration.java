package com.hsmty.tcs.config;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Configuration;

/**
 * <p>文本定制化生产模块 Mapper 扫描配置。
 *
 * <p>只扫描本模块 {@code com.hsmty.tcs.mapper}，避免多模块互相扫描。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Configuration
@MapperScan("com.hsmty.tcs.mapper")
public class TcsMapperScanConfiguration {
}
