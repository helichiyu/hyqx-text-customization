package com.wbdz;

import com.mybatisflex.spring.boot.MybatisFlexAutoConfiguration;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 文本定制化生产平台启动类。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@SpringBootApplication
@MapperScan("com.wbdz.mapper")
public class WbdzApplication {

    public static void main(String[] args) {
        SpringApplication.run(WbdzApplication.class, args);
    }
}
