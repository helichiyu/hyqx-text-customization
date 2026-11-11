package com.hsmty.tcs.common;

import cn.hutool.core.util.ObjectUtil;
import com.hsmty.security.user.SecurityUser;
import com.hsmty.security.user.UserInfoDetails;

/**
 * <p>当前操作人上下文。
 *
 * <p>登录态由 UAP/SSO Cookie 承载，框架通过 {@link SecurityUser} 暴露当前用户。
 * 异步编排线程没有登录上下文，统一记为 {@code system}，用于业务留痕字段（非审计字段，
 * 审计字段 createId/updateId 由 {@code EntityChangeListener} 自行处理）。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public final class AuthContext {

    /**
     * 无登录上下文时的操作人标识。
     */
    public static final String SYSTEM = "system";

    private AuthContext() {
    }

    /**
     * <p>当前操作人展示名。
     *
     * @return 昵称，其次登录名，最后 {@code system}
     */
    public static String username() {
        UserInfoDetails user = currentUser();
        if (user == null) {
            return SYSTEM;
        }
        if (ObjectUtil.isNotEmpty(user.getName())) {
            return user.getName();
        }
        if (ObjectUtil.isNotEmpty(user.getLoginName())) {
            return user.getLoginName();
        }
        if (ObjectUtil.isNotEmpty(user.getUsername())) {
            return user.getUsername();
        }
        return SYSTEM;
    }

    /**
     * <p>当前用户主键（字符串形式）。
     *
     * @return 用户 ID，未登录返回 null
     */
    public static String userId() {
        UserInfoDetails user = currentUser();
        return user == null ? null : user.getId();
    }

    /**
     * <p>安全获取当前登录用户。
     *
     * @return 当前用户，未登录或框架异常时返回 null
     */
    public static UserInfoDetails currentUser() {
        try {
            return SecurityUser.getUser();
        } catch (Exception e) {
            return null;
        }
    }
}
