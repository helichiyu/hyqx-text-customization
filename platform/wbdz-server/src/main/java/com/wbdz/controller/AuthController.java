package com.wbdz.controller;

import com.wbdz.common.ApiResult;
import com.wbdz.common.AuthContext;
import com.wbdz.dto.LoginDTO;
import com.wbdz.service.AuthService;
import com.wbdz.vo.CurrentUserVO;
import com.wbdz.vo.LoginVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 登录与当前用户。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Tag(name = "认证", description = "登录和当前用户")
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @Operation(summary = "登录")
    @PostMapping("/login")
    public ApiResult<LoginVO> login(@Valid @RequestBody LoginDTO dto) {
        String token = authService.login(dto.username(), dto.password());
        return ApiResult.success(new LoginVO(token));
    }

    /** 当前登录人（拦截器已校验 token；此处返回上下文中的用户信息）。 */
    @Operation(summary = "查询当前登录用户")
    @GetMapping("/me")
    public ApiResult<CurrentUserVO> me() {
        var user = AuthContext.get();
        return ApiResult.success(new CurrentUserVO(user.getId(), user.getUsername(), user.getNickname()));
    }
}