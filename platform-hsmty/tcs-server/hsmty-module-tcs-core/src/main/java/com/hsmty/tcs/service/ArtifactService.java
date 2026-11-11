package com.hsmty.tcs.service;

import com.hsmty.tcs.pojo.vo.ArtifactFileVO;

import java.util.List;

/**
 * <p>算子产物文件服务：通过算子文件接口列出/读取环节输出，平台不直接访问算子本地目录。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public interface ArtifactService {

    /**
     * <p>列出环节输出目录内文件（相对路径 + 大小）。
     *
     * @param runId 环节执行记录内部主键
     * @return 文件清单
     */
    List<ArtifactFileVO> list(Long runId);

    /**
     * <p>读取环节输出目录内文件。
     *
     * @param runId 环节执行记录内部主键
     * @param name  相对路径
     * @return 文件内容
     */
    byte[] read(Long runId, String name);
}
