package com.wbdz.common;

import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

/**
 * 全局异常处理：统一转换为 ApiResult 信封。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BizException.class)
    public ApiResult<Void> biz(BizException e) {
        return ApiResult.error(1, e.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ApiResult<Void> invalid(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(f -> f.getField() + " " + f.getDefaultMessage())
                .findFirst().orElse("参数校验失败");
        return ApiResult.error(1, msg);
    }

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ApiResult<Void> uploadTooLarge(MaxUploadSizeExceededException e) {
        return ApiResult.error(1, "上传文件超过大小限制");
    }

    @ExceptionHandler(Exception.class)
    public ApiResult<Void> unknown(Exception e) {
        log.error("未处理异常: {}", e.getMessage(), e);
        return ApiResult.error(1, "系统异常，请稍后重试");
    }
}
