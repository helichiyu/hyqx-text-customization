package com.hsmty.tcs.operator;

import java.util.List;
import java.util.Map;

/**
 * <p>算子产物文件访问抽象。
 *
 * <p>算子独立部署在其它容器/服务器，平台不共享其文件系统，产物只能通过接口读取。
 * 生产形态使用 {@link HttpOperatorFileService}（算子需实现 {@code /listFiles}、
 * {@code /downloadFile}、{@code /progress} 三个接口，见 {@code docs/算子文件接口约定.md}）；
 * 本地联调若平台与算子挂载了同一运行目录，可切换 {@link LocalOperatorFileService}。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public interface OperatorFileService {

    /**
     * <p>列出产物路径下的文件。
     *
     * <p>路径既可能是目录（中段算子输出），也可能是压缩包（末位环节产物）；
     * 两种形态都返回可直接用于 {@link #readEntry(String, String, String)} 的条目名。
     *
     * @param tag  算子标识
     * @param path 算子返回的产物路径
     * @return 文件条目（名称为相对路径）
     */
    List<OperatorFile> list(String tag, String path);

    /**
     * <p>读取产物路径下指定条目。
     *
     * @param tag  算子标识
     * @param path 产物路径（目录或压缩包）
     * @param name 条目名（{@link #list(String, String)} 返回的名称）
     * @return 文件字节
     */
    byte[] readEntry(String tag, String path, String name);

    /**
     * <p>读取环节样本级实时进度。
     *
     * @param tag   算子标识
     * @param runId 环节执行记录主键
     * @return 进度对象，尚未生成或不可用时返回 null
     */
    Map<String, Object> progress(String tag, Long runId);

    /**
     * <p>产物文件条目。
     *
     * @param name 相对路径
     * @param size 文件大小，单位字节
     */
    record OperatorFile(String name, long size) {
    }
}
