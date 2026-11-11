package com.hsmty.tcs.service.impl;

import com.hsmty.core.util.JsonUtils;
import com.hsmty.tcs.common.AuthContext;
import com.hsmty.tcs.common.BizException;
import com.hsmty.tcs.common.Times;
import com.hsmty.tcs.mapper.ParamDraftMapper;
import com.hsmty.tcs.mapper.ParamVersionMapper;
import com.hsmty.tcs.operator.LineRegistry;
import com.hsmty.tcs.pojo.po.ParamDraftEntity;
import com.hsmty.tcs.pojo.po.ParamVersionEntity;
import com.hsmty.tcs.pojo.vo.ParamLineConfigVO;
import com.hsmty.tcs.pojo.vo.ParamOverviewVO;
import com.hsmty.tcs.pojo.vo.ParamVersionVO;
import com.hsmty.tcs.service.ParamService;
import com.mybatisflex.core.query.QueryWrapper;
import com.mybatisflex.spring.service.impl.ServiceImpl;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.type.TypeReference;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * <p>参数配置：草稿保存 / 发布版本（任务创建锁定快照）。
 *
 * <p>版本号自增：v1.0 → v1.1 → v1.2…；发布后草稿清除。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Service
@RequiredArgsConstructor
public class ParamServiceImpl extends ServiceImpl<ParamVersionMapper, ParamVersionEntity>
        implements ParamService {

    private static final TypeReference<List<Map<String, Object>>> GROUP_LIST =
            new TypeReference<List<Map<String, Object>>>() {
            };

    private final ParamVersionMapper versionMapper;

    private final ParamDraftMapper draftMapper;

    /**
     * 产线配置页数据：最新已发布版本 + 草稿（无草稿时草稿内容取最新版本）。
     */
    @Override
    public ParamLineConfigVO lineConfig(String line) {
        requireLine(line);
        ParamLineConfigVO config = new ParamLineConfigVO();
        ParamVersionEntity latest = latest(line);
        ParamDraftEntity draft = draftMapper.selectOneByQuery(QueryWrapper.create()
                .where("line = ?", line));
        config.setLine(line);
        config.setLineName("common".equals(line) ? "公共规则" : LineRegistry.LINE_NAMES.get(line));
        config.setLatest(toVO(latest));
        config.setHasDraft(draft != null);
        config.setDraft(toVO(draft == null ? latest : draftToVersion(draft)));
        config.setVersions(versionMapper.selectListByQuery(QueryWrapper.create()
                        .where("line = ?", line)
                        .orderBy("published_at desc")).stream()
                .map(this::toVO).toList());
        return config;
    }

    /**
     * 全部产线概览（任务创建时选择参数版本用）。
     */
    @Override
    public List<ParamOverviewVO> overview() {
        List<ParamOverviewVO> out = new ArrayList<>();
        for (String line : LineRegistry.LINE_NAMES.keySet().stream().sorted().toList()) {
            ParamVersionEntity version = latest(line);
            ParamOverviewVO row = new ParamOverviewVO();
            row.setLine(line);
            row.setLineName(LineRegistry.LINE_NAMES.get(line));
            row.setVersion(version == null ? null : version.getVersion());
            row.setPublishedAt(version == null ? null : Times.text(version.getPublishedAt()));
            out.add(row);
        }
        return out;
    }

    /**
     * 保存草稿（每产线一份，覆盖式）。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void saveDraft(String line, String content) {
        requireLine(line);
        String normalized = validate(content);
        ParamDraftEntity draft = draftMapper.selectOneByQuery(QueryWrapper.create()
                .where("line = ?", line));
        if (draft == null) {
            draft = new ParamDraftEntity();
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

    /**
     * 发布：草稿（或传入内容）→ 新版本，版本号自增，草稿清除。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public ParamVersionVO publish(String line, String content) {
        requireLine(line);
        String normalized = content != null ? validate(content) : draftContent(line);
        ParamVersionEntity latest = latest(line);
        String next = ParamService.bump(latest == null ? null : latest.getVersion());
        ParamVersionEntity v = new ParamVersionEntity();
        v.setLine(line);
        v.setVersion(next);
        v.setContent(normalized);
        v.setPublishedAt(LocalDateTime.now());
        v.setPublishedBy(AuthContext.username());
        versionMapper.insert(v);
        draftMapper.deleteByQuery(QueryWrapper.create().where("line = ?", line));
        return toVO(v);
    }

    /**
     * 最新已发布版本（任务创建 / 素材准入取值来源）。
     */
    @Override
    public ParamVersionEntity latest(String line) {
        return versionMapper.selectOneByQuery(QueryWrapper.create()
                .where("line = ?", line)
                .orderBy("published_at desc").limit(1));
    }

    private String draftContent(String line) {
        ParamDraftEntity draft = draftMapper.selectOneByQuery(QueryWrapper.create()
                .where("line = ?", line));
        if (draft == null) {
            throw new BizException("没有可发布的草稿，请先保存草稿");
        }
        return draft.getContent();
    }

    /**
     * 校验参数组：JSON 数组，每项含非空 name/value；返回规范化后的 JSON。
     */
    private String validate(String content) {
        if (content == null || content.isBlank()) {
            throw new BizException("参数内容不能为空");
        }
        List<Map<String, Object>> groups;
        try {
            groups = JsonUtils.parseArray(content, GROUP_LIST);
        } catch (Exception e) {
            throw new BizException("参数内容必须是 JSON 数组：[{name,value,desc}]", e);
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
        return JsonUtils.toJsonString(groups);
    }

    private void requireLine(String line) {
        if (!"common".equals(line) && !LineRegistry.LINE_NAMES.containsKey(line)) {
            throw new BizException("产线不存在");
        }
    }

    private ParamVersionEntity draftToVersion(ParamDraftEntity d) {
        ParamVersionEntity v = new ParamVersionEntity();
        v.setLine(d.getLine());
        v.setVersion("draft");
        v.setContent(d.getContent());
        v.setPublishedAt(d.getUpdateTime());
        v.setPublishedBy(d.getUpdateBy());
        return v;
    }

    private ParamVersionVO toVO(ParamVersionEntity version) {
        if (version == null) {
            return null;
        }
        ParamVersionVO vo = new ParamVersionVO();
        vo.setLine(version.getLine());
        vo.setVersion(version.getVersion());
        vo.setContent(version.getContent() == null || version.getContent().isBlank()
                ? List.of() : JsonUtils.parseArray(version.getContent(), GROUP_LIST));
        vo.setPublishedAt(Times.text(version.getPublishedAt()));
        vo.setPublishedBy(version.getPublishedBy());
        return vo;
    }
}
