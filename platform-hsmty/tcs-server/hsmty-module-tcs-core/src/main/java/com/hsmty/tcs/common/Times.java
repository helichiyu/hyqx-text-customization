package com.hsmty.tcs.common;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * <p>时间展示格式化：VO 中的时间统一为 {@code yyyy-MM-dd HH:mm:ss} 字符串。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public final class Times {

    private static final DateTimeFormatter DATE_TIME =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static final DateTimeFormatter MINUTE =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    private Times() {
    }

    /**
     * <p>格式化为秒级时间字符串。
     *
     * @param time 时间
     * @return 格式字符串；入参为空时返回 null
     */
    public static String text(LocalDateTime time) {
        return time == null ? null : time.format(DATE_TIME);
    }

    /**
     * <p>格式化为分钟级时间字符串。
     *
     * @param time 时间
     * @return 格式字符串；入参为空时返回 {@code -}
     */
    public static String minute(LocalDateTime time) {
        return time == null ? "-" : time.format(MINUTE);
    }
}
