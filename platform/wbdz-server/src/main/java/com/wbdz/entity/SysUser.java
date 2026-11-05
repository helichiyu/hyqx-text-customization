package com.wbdz.entity;

import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 用户（单角色）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
@Table(value = "wbdz_user", onInsert = AuditListener.class, onUpdate = AuditListener.class)
@Schema(description = "系统用户")
public class SysUser implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id(keyType = KeyType.Generator, value = "flexId")
    @Schema(description = "内部主键")
    private Long id;

    @Schema(description = "登录名")
    private String username;

    /** BCrypt 密文。 */
    @Schema(description = "密码哈希")
    private String password;

    /** 展示名（操作人）。 */
    @Schema(description = "昵称")
    private String nickname;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
