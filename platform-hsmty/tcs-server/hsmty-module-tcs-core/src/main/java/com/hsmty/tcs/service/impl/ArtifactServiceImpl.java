package com.hsmty.tcs.service.impl;

import com.hsmty.tcs.common.BizException;
import com.hsmty.tcs.mapper.TaskStageRunMapper;
import com.hsmty.tcs.operator.OperatorFileService;
import com.hsmty.tcs.pojo.po.TaskStageRunEntity;
import com.hsmty.tcs.pojo.vo.ArtifactFileVO;
import com.hsmty.tcs.service.ArtifactService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.List;

/**
 * <p>算子产物文件服务：产物文件通过 {@link OperatorFileService} 从算子侧获取，
 * 平台不挂载、不直接访问算子本地目录。
 *
 * <p>安全：只允许访问环节输出目录之内的相对路径，拒绝目录穿越。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Service
@RequiredArgsConstructor
public class ArtifactServiceImpl implements ArtifactService {

    private final TaskStageRunMapper stageRunMapper;

    private final OperatorFileService fileService;

    /**
     * 环节输出目录内文件清单（相对路径 + 大小）。
     */
    @Override
    public List<ArtifactFileVO> list(Long runId) {
        TaskStageRunEntity run = load(runId);
        return fileService.list(run.getOperatorTag(), run.getOutputPath()).stream()
                .map(file -> new ArtifactFileVO(file.name(), file.size()))
                .sorted(Comparator.comparing(ArtifactFileVO::name))
                .toList();
    }

    /**
     * 读取环节输出目录内文件。
     */
    @Override
    public byte[] read(Long runId, String name) {
        TaskStageRunEntity run = load(runId);
        return fileService.readEntry(run.getOperatorTag(), run.getOutputPath(), safeName(name));
    }

    private TaskStageRunEntity load(Long runId) {
        TaskStageRunEntity run = stageRunMapper.selectOneById(runId);
        if (run == null || run.getOutputPath() == null || run.getOutputPath().isBlank()) {
            throw new BizException("环节执行记录不存在或尚无输出");
        }
        return run;
    }

    /**
     * 校验相对路径：禁止绝对路径与 {@code ..} 目录穿越。
     */
    private String safeName(String name) {
        String cleaned = name == null ? "" : name.replace('\\', '/');
        if (cleaned.isBlank() || cleaned.startsWith("/") || cleaned.contains("../")
                || cleaned.contains("/..") || cleaned.equals("..")) {
            throw new BizException("路径越界（仅允许环节输出目录之内）");
        }
        return cleaned;
    }
}
