package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户（单角色）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_user", onInsert = AuditListener.class, onUpdate = AuditListener.class)
public class SysUser {

    @Id(keyType = KeyType.Generator, value = "flexId")
    private Long id;

    private String username;

    /** BCrypt 密文。 */
    private String password;

    /** 展示名（操作人）。 */
    private String nickname;

    private LocalDateTime createTime;
}
