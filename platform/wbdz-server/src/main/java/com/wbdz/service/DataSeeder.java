package com.wbdz.service;

import com.wbdz.entity.ParamVersion;
import com.wbdz.entity.SysUser;
import com.wbdz.mapper.ParamVersionMapper;
import com.wbdz.mapper.SysUserMapper;
import com.mybatisflex.core.query.QueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static com.wbdz.entity.table.ParamVersionTableDef.PARAM_VERSION;
import static com.wbdz.entity.table.SysUserTableDef.SYS_USER;

/**
 * 种子数据：初始账号与各产线参数版本 v1.0（幂等）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DataSeeder implements ApplicationRunner {

    private final SysUserMapper userMapper;

    private final ParamVersionMapper paramVersionMapper;

    @Override
    public void run(ApplicationArguments args) {
        if (userMapper.selectCountByQuery(QueryWrapper.create().where(SYS_USER.USERNAME.eq("admin"))) == 0) {
            SysUser admin = new SysUser();
            admin.setUsername("admin");
            admin.setPassword(new BCryptPasswordEncoder().encode("admin123"));
            admin.setNickname("管理员");
            userMapper.insert(admin);
            log.info("种子：创建初始账号 admin/admin123");
        }
        seedParam("formula", List.of(
                Map.of("name", "并发数", "value", "4-8", "desc", "单任务并行处理的公式数；阈值在数据集明细按任务调整。")));
        seedParam("layout", List.of(
                Map.of("name", "渲染 DPI", "value", "150", "desc", "逐页渲染分辨率，范围 72-300。"),
                Map.of("name", "并发数", "value", "4-8", "desc", "单任务逐页调用模型的并发数。")));
        seedParam("graphic", List.of(
                Map.of("name", "并发数", "value", "4-8", "desc", "单任务逐张调用模型的并发数。")));
        seedParam("metadata", List.of(
                Map.of("name", "并发数", "value", "4-8", "desc", "单任务文档处理并发数。")));
        seedParam("common", List.of(
                Map.of("name", "单文件大小上限(MB)", "value", "50", "desc", "素材准入校验用，全部产线。"),
                Map.of("name", "图片最小分辨率", "value", "600", "desc", "图文融合素材准入校验用。")));
    }

    private void seedParam(String line, List<Map<String, String>> groups) {
        if (paramVersionMapper.selectCountByQuery(QueryWrapper.create()
                .where(PARAM_VERSION.LINE.eq(line))) > 0) {
            return;
        }
        ParamVersion v = new ParamVersion();
        v.setLine(line);
        v.setVersion("v1.0");
        v.setContent(com.wbdz.common.JsonUtil.write(groups));
        v.setPublishedAt(LocalDateTime.now());
        v.setPublishedBy("system");
        paramVersionMapper.insert(v);
    }
}
