package com.wbdz.config;

import com.wbdz.common.AuthContext;
import com.wbdz.common.JwtUtil;
import com.wbdz.entity.SysUser;
import com.wbdz.mapper.SysUserMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.lang.NonNull;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web 配置：JWT 登录拦截 + 前端开发跨域。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Configuration
@RequiredArgsConstructor
public class WebConfig implements WebMvcConfigurer {

    private final JwtUtil jwtUtil;

    private final SysUserMapper sysUserMapper;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new HandlerInterceptor() {
            @Override
            public boolean preHandle(@NonNull HttpServletRequest request,
                                     @NonNull HttpServletResponse response,
                                     @NonNull Object handler) throws Exception {
                if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
                    return true;
                }
                String auth = request.getHeader("Authorization");
                String token = auth != null && auth.startsWith("Bearer ") ? auth.substring(7) : null;
                Long userId = token == null ? null : jwtUtil.parseUserId(token);
                SysUser user = userId == null ? null : sysUserMapper.selectOneById(userId);
                if (user == null) {
                    response.setStatus(401);
                    response.setContentType("application/json;charset=UTF-8");
                    response.getWriter().write("{\"code\":401,\"msg\":\"未登录或登录已过期\",\"data\":null}");
                    return false;
                }
                AuthContext.set(user);
                return true;
            }

            @Override
            public void afterCompletion(@NonNull HttpServletRequest request,
                                        @NonNull HttpServletResponse response,
                                        @NonNull Object handler, Exception ex) {
                AuthContext.clear();
            }
        }).addPathPatterns("/**")
          .excludePathPatterns("/api/auth/login", "/api/healthz", "/error");
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("*")
                .allowedHeaders("*");
    }
}
