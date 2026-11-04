package com.wbdz.common;

import lombok.Getter;

/**
 * 业务异常：message 直接面向前端展示（中文）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Getter
public class BizException extends RuntimeException {

    public BizException(String message) {
        super(message);
    }
}
