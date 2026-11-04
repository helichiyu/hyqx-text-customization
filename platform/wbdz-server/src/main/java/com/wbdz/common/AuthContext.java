package com.wbdz.common;

import com.wbdz.entity.SysUser;

/**
 * 当前登录人上下文（编排等异步线程中可能为空，写入类操作均在请求线程内）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
public final class AuthContext {

    private static final ThreadLocal<SysUser> HOLDER = new ThreadLocal<>();

    private AuthContext() {
    }

    public static void set(SysUser user) {
        HOLDER.set(user);
    }

    public static SysUser get() {
        return HOLDER.get();
    }

    /** 当前登录人名，无上下文时返回系统占位（异步任务写入用）。 */
    public static String username() {
        SysUser u = HOLDER.get();
        return u == null ? "system" : u.getNickname();
    }

    public static void clear() {
        HOLDER.remove();
    }
}
