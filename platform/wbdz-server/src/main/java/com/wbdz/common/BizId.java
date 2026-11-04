package com.wbdz.common;

import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

/**
 * 业务编号生成器：前缀 + yyMMdd + 6 位随机码。
 *
 * <p>随机码字符集按平台 ID 规范去掉易混淆字符（0/O/1/I/L），共 31 个安全字符，
 * 使用 CSPRNG 生成。调用方负责落库时唯一约束与碰撞重试。
 *
 * @author wbdz
 * @since 2026-11-03
 */
public final class BizId {

    /** 31 个安全字符：数字 2-9 + 大写字母（去 I/L/O）。 */
    private static final String SAFE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";

    private static final SecureRandom RANDOM = new SecureRandom();

    private static final DateTimeFormatter YYMMDD = DateTimeFormatter.ofPattern("yyMMdd");

    /** 产线短前缀（素材批次 / 交付 / 回滚记录使用）。 */
    public static final List<String> LINE_PREFIXES = List.of("GS", "FZ", "TW", "YX");

    private BizId() {
    }

    /**
     * 生成业务编号。
     *
     * @param prefix 2-4 位大写字母前缀（TASK/DS/CR/GS/FZ/TW/YX 等）
     */
    public static String next(String prefix) {
        StringBuilder sb = new StringBuilder(prefix.length() + 12);
        sb.append(prefix).append(LocalDateTime.now().format(YYMMDD));
        for (int i = 0; i < 6; i++) {
            sb.append(SAFE_CHARS.charAt(RANDOM.nextInt(SAFE_CHARS.length())));
        }
        return sb.toString();
    }
}
