package com.wbdz.service.impl;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.service.ParamService;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.AuthContext;
import com.wbdz.service.ParamService;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.BizException;
import com.wbdz.service.ParamService;
import com.wbdz.service.LineRegistry;
import com.wbdz.common.JsonUtil;
import com.wbdz.entity.ParamDraft;
import com.wbdz.entity.ParamVersion;
import com.wbdz.mapper.ParamDraftMapper;
import com.wbdz.mapper.ParamVersionMapper;
import com.wbdz.vo.ParamLineConfigVO;
import com.wbdz.vo.ParamOverviewVO;
import com.wbdz.vo.ParamVersionVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static com.wbdz.entity.table.ParamDraftTableDef.PARAM_DRAFT;
import static com.wbdz.entity.table.ParamVersionTableDef.PARAM_VERSION;

/**
 * 参数配置：草稿保存 / 发布版本（任务创建锁定快照）。
 *
 * <p>版本号自增：v1.0 → v1.1 → v1.2…；发布后草稿清除。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Service
@RequiredArgsConstructor
public class ParamServiceImpl implements ParamService {

    private final ParamVersionMapper versionMapper;

    private final ParamDraftMapper draftMapper;

    /** 产线配置页数据：最新已发布版本 + 草稿（无草稿时草稿内容取最新版本）。 */
    public ParamLineConfigVO lineConfig(String line) {
        requireLine(line);
        ParamLineConfigVO config = new ParamLineConfigVO();
        ParamVersion latest = latest(line);
        ParamDraft draft = draftMapper.selectOneByQuery(QueryWrapper.create()
                .where(PARAM_DRAFT.LINE.eq(line)));
        config.setLine(line);
        config.setLineName("common".equals(line) ? "公共规则" : LineRegistry.LINE_NAMES.get(line));
        config.setLatest(toVO(latest));
        config.setHasDraft(draft != null);
        config.setDraft(toVO(draft == null ? latest : draftToVersion(draft)));
        config.setVersions(versionMapper.selectListByQuery(QueryWrapper.create()
                        .where(PARAM_VERSION.LINE.eq(line))
                        .orderBy(PARAM_VERSION.PUBLISHED_AT.desc())).stream()
                .map(this::toVO).toList());
        return config;
    }

    /** 全部产线概览（任务创建时选择参数版本用）。 */
    public List<ParamOverviewVO> overview() {
        List<ParamOverviewVO> out = new ArrayList<>();
        for (String line : LineRegistry.LINE_NAMES.keySet().stream().sorted().toList()) {
            ParamVersion version = latest(line);
            ParamOverviewVO row = new ParamOverviewVO();
            row.setLine(line);
            row.setLineName(LineRegistry.LINE_NAMES.get(line));
            row.setVersion(version == null ? null : version.getVersion());
            row.setPublishedAt(version == null ? null : String.valueOf(version.getPublishedAt()));
            out.add(row);
        }
        return out;
    }
    /** 保存草稿（每产线一份，覆盖式）。 */
    @Transactional(rollbackFor = Exception.class)
    public void saveDraft(String line, String content) {
        requireLine(line);
        String normalized = validate(content);
        ParamDraft draft = draftMapper.selectOneByQuery(QueryWrapper.create()
                .where(PARAM_DRAFT.LINE.eq(line)));
        if (draft == null) {
            draft = new ParamDraft();
            draft.setLine(line);
            draft.setContent(normalized);
            draft.setUpdateBy(AuthContext.username());
            draftMapper.insert(draft);
        } else {
            draft.setContent(normalized);
            draft.setUpdateBy(AuthContext.username());
            draftMapper.update(draft);
        }
    }

    /** 发布：草稿（或传入内容）→ 新版本，版本号自增，草稿清除。 */
    @Transactional(rollbackFor = Exception.class)
    public ParamVersionVO publish(String line, String content) {
        requireLine(line);
        String normalized = content != null ? validate(content) : draftContent(line);
        ParamVersion latest = latest(line);
        String next = ParamService.bump(latest == null ? null : latest.getVersion());
        ParamVersion v = new ParamVersion();
        v.setLine(line);
        v.setVersion(next);
        v.setContent(normalized);
        v.setPublishedAt(LocalDateTime.now());
        v.setPublishedBy(AuthContext.username());
        versionMapper.insert(v);
        draftMapper.deleteByQuery(QueryWrapper.create().where(PARAM_DRAFT.LINE.eq(line)));
        return toVO(v);
    }

    /** 最新已发布版本（任务创建/素材准入取值来源）。 */
    public ParamVersion latest(String line) {
        return versionMapper.selectOneByQuery(QueryWrapper.create()
                .where(PARAM_VERSION.LINE.eq(line))
                .orderBy(PARAM_VERSION.PUBLISHED_AT.desc()).limit(1));
    }

    private String draftContent(String line) {
        ParamDraft draft = draftMapper.selectOneByQuery(QueryWrapper.create()
                .where(PARAM_DRAFT.LINE.eq(line)));
        if (draft == null) {
            throw new BizException("没有可发布的草稿，请先保存草稿");
        }
        return draft.getContent();
    }

    /** 校验参数组：JSON 数组，每项含非空 name/value；返回规范化后的 JSON。 */
    private String validate(String content) {
        if (content == null || content.isBlank()) {
            throw new BizException("参数内容不能为空");
        }
        List<Map<String, Object>> groups;
        try {
            groups = JsonUtil.readList(content);
        } catch (Exception e) {
            throw new BizException("参数内容必须是 JSON 数组：[{name,value,desc}]");
        }
        if (groups.isEmpty()) {
            throw new BizException("至少保留一个参数组");
        }
        for (Map<String, Object> g : groups) {
            if (g.get("name") == null || String.valueOf(g.get("name")).isBlank()) {
                throw new BizException("参数组 name 不能为空");
            }
            if (g.get("value") == null || String.valueOf(g.get("value")).isBlank()) {
                throw new BizException("参数「" + g.get("name") + "」的值不能为空");
            }
        }
        return JsonUtil.write(groups);
    }


    private void requireLine(String line) {
        if (!"common".equals(line) && !LineRegistry.LINE_NAMES.containsKey(line)) {
            throw new BizException("产线不存在");
        }
    }

    private ParamVersion draftToVersion(ParamDraft d) {
        ParamVersion v = new ParamVersion();
        v.setLine(d.getLine());
        v.setVersion("draft");
        v.setContent(d.getContent());
        v.setPublishedAt(d.getUpdateTime());
        v.setPublishedBy(d.getUpdateBy());
        return v;
    }

    private ParamVersionVO toVO(ParamVersion version) {
        return ParamVersionVO.from(version);
    }
}
