package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.AuthContext;
import com.wbdz.dto.LoginDTO;
import com.wbdz.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 登录与当前用户。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ApiResult<Map<String, Object>> login(@Valid @RequestBody LoginDTO dto) {
        String token = authService.login(dto.username(), dto.password());
        return ApiResult.success(Map.of("token", token));
    }

    /** 当前登录人（拦截器已校验 token；此处返回上下文中的用户信息）。 */
    @GetMapping("/me")
    public ApiResult<Map<String, Object>> me() {
        var user = AuthContext.get();
        return ApiResult.success(Map.of(
                "id", user.getId(),
                "username", user.getUsername(),
                "nickname", user.getNickname()));
    }
}
