package com.wbdz.service;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.common.BizException;
import com.wbdz.common.JwtUtil;
import com.wbdz.entity.SysUser;
import com.wbdz.mapper.SysUserMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import static com.wbdz.entity.table.SysUserTableDef.SYS_USER;

/**
 * 登录（单角色，账号密码 + JWT）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Service
@RequiredArgsConstructor
public class AuthService {

    private final SysUserMapper userMapper;

    private final JwtUtil jwtUtil;

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    public String login(String username, String password) {
        SysUser user = userMapper.selectOneByQuery(QueryWrapper.create().where(SYS_USER.USERNAME.eq(username)));
        if (user == null || !encoder.matches(password, user.getPassword())) {
            throw new BizException("账号或密码错误");
        }
        return jwtUtil.issue(user.getId(), user.getNickname());
    }
}
