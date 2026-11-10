package com.hsmty;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.EnableAspectJAutoProxy;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * <p>启动类关键注解断言，防止误删。
 *
 * @author helichiyu
 * @since 2.0.1
 */
class RunApplicationTest {

    @Test
    void shouldKeepRequiredAnnotations() {
        assertThat(RunApplication.class.isAnnotationPresent(SpringBootApplication.class)).isTrue();
        assertThat(RunApplication.class.isAnnotationPresent(EnableAspectJAutoProxy.class)).isTrue();
        assertThat(RunApplication.class.isAnnotationPresent(EnableFeignClients.class)).isTrue();
    }
}
