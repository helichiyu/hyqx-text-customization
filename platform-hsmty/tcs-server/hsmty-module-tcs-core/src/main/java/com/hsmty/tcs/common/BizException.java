package com.hsmty.tcs.common;

import com.hsmty.core.common.enums.CommonResponseEnum;
import com.hsmty.core.common.exception.common.BusinessException;

/**
 * <p>文本定制化生产业务异常。
 *
 * <p>继承框架统一业务异常，由 {@code GlobalExceptionHandler} 转换为标准响应；
 * 业务码统一使用 {@link CommonResponseEnum#INVALID}，具体原因由 message 表达。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public class BizException extends BusinessException {

    private static final long serialVersionUID = 1L;

    /**
     * <p>构造业务异常。
     *
     * @param message 业务错误信息
     */
    public BizException(String message) {
        super(CommonResponseEnum.INVALID, null, message);
    }

    /**
     * <p>构造带原因的业务异常。
     *
     * @param message 业务错误信息
     * @param cause   原始异常
     */
    public BizException(String message, Throwable cause) {
        super(CommonResponseEnum.INVALID, null, message, cause);
    }
}
