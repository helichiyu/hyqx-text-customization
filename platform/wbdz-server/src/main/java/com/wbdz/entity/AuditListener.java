package com.wbdz.entity;

import com.mybatisflex.annotation.InsertListener;
import com.mybatisflex.annotation.UpdateListener;
import com.wbdz.common.AuthContext;

import java.lang.reflect.Field;
import java.time.LocalDateTime;

/**
 * 审计字段统一填充：插入时补 createTime/updateTime/createBy/updateBy，更新时刷新 updateTime/updateBy。
 *
 * <p>通过 {@code @Table(onInsert = AuditListener.class, onUpdate = AuditListener.class)} 挂载，
 * 业务代码不再手写这四个字段；异步编排线程无登录上下文时记为 system。
 *
 * @author wbdz
 * @since 2026-11-03
 */
public class AuditListener implements InsertListener, UpdateListener {

    @Override
    public void onInsert(Object entity) {
        LocalDateTime now = LocalDateTime.now();
        String user = AuthContext.username();
        fillIfNull(entity, "createTime", now);
        fillIfNull(entity, "updateTime", now);
        fillIfNull(entity, "createBy", user);
        fillIfNull(entity, "updateBy", user);
    }

    @Override
    public void onUpdate(Object entity) {
        forceSet(entity, "updateTime", LocalDateTime.now());
        forceSet(entity, "updateBy", AuthContext.username());
    }

    private static void fillIfNull(Object entity, String name, Object value) {
        if (value == null) {
            return;
        }
        Object current = read(entity, name);
        if (current == null) {
            forceSet(entity, name, value);
        }
    }

    private static Object read(Object entity, String name) {
        try {
            Field f = entity.getClass().getDeclaredField(name);
            f.setAccessible(true);
            return f.get(entity);
        } catch (ReflectiveOperationException e) {
            return null;
        }
    }

    private static void forceSet(Object entity, String name, Object value) {
        try {
            Field f = entity.getClass().getDeclaredField(name);
            f.setAccessible(true);
            f.set(entity, value);
        } catch (ReflectiveOperationException ignored) {
            // 实体无该字段时跳过
        }
    }
}
