package com.wbdz.config;

import com.wbdz.common.JwtUtil;
import com.wbdz.mapper.SysUserMapper;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;

import java.lang.reflect.Field;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * JWT 拦截器未登录响应测试。
 *
 * @author wbdz
 * @since 2026-11-05
 */
class WebConfigTest {

    @Test
    void requestWithoutTokenReturnsUnauthorized() throws Exception {
        JwtUtil jwtUtil = new JwtUtil("wbdz-test-jwt-secret-key-at-least-32-bytes", 1);
        WebConfig config = new WebConfig(jwtUtil, mock(SysUserMapper.class));
        InterceptorRegistry registry = new InterceptorRegistry();
        config.addInterceptors(registry);
        Field registrationsField = InterceptorRegistry.class.getDeclaredField("registrations");
        registrationsField.setAccessible(true);
        List<?> registrations = (List<?>) registrationsField.get(registry);
        Field interceptorField = registrations.getFirst().getClass().getDeclaredField("interceptor");
        interceptorField.setAccessible(true);
        HandlerInterceptor interceptor = (HandlerInterceptor) interceptorField.get(registrations.getFirst());

        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/task");
        MockHttpServletResponse response = new MockHttpServletResponse();
        boolean allowed = interceptor.preHandle(request, response, new Object());

        assertThat(allowed).isFalse();
        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(response.getContentAsString()).contains("未登录或登录已过期");
    }


}