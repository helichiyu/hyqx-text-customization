package com.wbdz.common;

import lombok.Data;

/**
 * 统一接口返回信封。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
public class ApiResult<T> {

    private int code;
    private String msg;
    private T data;

    public static <T> ApiResult<T> success() {
        return build(0, "success", null);
    }

    public static <T> ApiResult<T> success(T data) {
        return build(0, "success", data);
    }

    public static <T> ApiResult<T> error(int code, String msg) {
        return build(code, msg, null);
    }

    public static <T> ApiResult<T> error(String msg) {
        return build(1, msg, null);
    }

    private static <T> ApiResult<T> build(int code, String msg, T data) {
        ApiResult<T> r = new ApiResult<>();
        r.code = code;
        r.msg = msg;
        r.data = data;
        return r;
    }
}
