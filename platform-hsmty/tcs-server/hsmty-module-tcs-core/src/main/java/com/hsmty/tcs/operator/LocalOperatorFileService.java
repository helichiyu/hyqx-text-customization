package com.hsmty.tcs.operator;

import com.hsmty.core.util.JsonUtils;
import com.hsmty.tcs.common.BizException;
import com.hsmty.tcs.config.TcsOperatorProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * <p>本地模式产物读取：平台与算子共用运行时目录时直接读文件系统。
 *
 * <p>仅用于本地联调（{@code tcs.operator.file-mode=local}）。生产部署下算子文件系统不可见，
 * 必须使用 {@link HttpOperatorFileService}。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Slf4j
@Service
@ConditionalOnProperty(name = "tcs.operator.file-mode", havingValue = "local")
public class LocalOperatorFileService implements OperatorFileService {

    private final TcsOperatorProperties properties;

    public LocalOperatorFileService(TcsOperatorProperties properties) {
        this.properties = properties;
    }

    @Override
    public List<OperatorFile> list(String tag, String path) {
        Path target = toHostPath(path);
        if (Files.isDirectory(target)) {
            return listDirectory(target);
        }
        if (Files.isRegularFile(target)) {
            if (target.getFileName().toString().toLowerCase().endsWith(".zip")) {
                return listZip(target);
            }
            return List.of(new OperatorFile(target.getFileName().toString(), sizeOf(target)));
        }
        return List.of();
    }

    @Override
    public byte[] readEntry(String tag, String path, String name) {
        Path target = toHostPath(path);
        if (Files.isDirectory(target)) {
            Path file = target.resolve(name).normalize();
            if (!file.startsWith(target.normalize()) || !Files.isRegularFile(file)) {
                throw new BizException("产物文件不存在: " + name);
            }
            try {
                return Files.readAllBytes(file);
            } catch (IOException e) {
                throw new BizException("读取产物文件失败: " + name, e);
            }
        }
        return readZipEntry(target, name);
    }

    @Override
    public Map<String, Object> progress(String tag, Long runId) {
        if (runId == null) {
            return null;
        }
        Path runtimeRoot = Path.of(properties.getRuntimeDir());
        for (String outputDir : new String[]{"outputs", "output"}) {
            Path path = runtimeRoot.resolve(outputDir).resolve("_progress").resolve(runId + ".json");
            if (!Files.isRegularFile(path)) {
                continue;
            }
            try {
                return JsonUtils.jsonToMap(Files.readString(path, StandardCharsets.UTF_8));
            } catch (Exception e) {
                log.warn("读取算子进度失败: runId={} path={} err={}", runId, path, e.getMessage(), e);
            }
        }
        return null;
    }

    // ==================== 内部 ====================

    /**
     * <p>算子返回路径 → 本机路径。
     *
     * <p>部署形态下算子回 {@code /data/...}，按运行时根目录映射；本地进程直跑时算子在 Windows 上
     * 回 {@code E:\data\...} 形式的绝对路径，只要落在运行时根之下同样放行。闸外路径一律拒绝。
     */
    private Path toHostPath(String containerPath) {
        String p = containerPath == null ? "" : containerPath.replace("\\", "/");
        Path runtimeRoot = Path.of(properties.getRuntimeDir()).toAbsolutePath().normalize();
        if (p.startsWith("/data/")) {
            return runtimeRoot.resolve(p.substring("/data/".length())).normalize();
        }
        Path host = Path.of(p).toAbsolutePath().normalize();
        if (host.startsWith(runtimeRoot)) {
            return host;
        }
        throw new BizException("算子返回了闸外路径（仅支持 /data/ 或运行时目录之内）: " + containerPath);
    }

    private static List<OperatorFile> listDirectory(Path dir) {
        List<OperatorFile> out = new ArrayList<>();
        try (var walk = Files.walk(dir)) {
            walk.filter(Files::isRegularFile).forEach(file -> out.add(new OperatorFile(
                    dir.relativize(file).toString().replace('\\', '/'), sizeOf(file))));
        } catch (IOException e) {
            throw new BizException("读取产物目录失败: " + e.getMessage(), e);
        }
        out.sort((a, b) -> a.name().compareTo(b.name()));
        return out;
    }

    private static List<OperatorFile> listZip(Path zip) {
        List<OperatorFile> out = new ArrayList<>();
        try (ZipInputStream zin = new ZipInputStream(Files.newInputStream(zip), StandardCharsets.UTF_8)) {
            ZipEntry entry;
            while ((entry = zin.getNextEntry()) != null) {
                if (entry.isDirectory()) {
                    continue;
                }
                out.add(new OperatorFile(entry.getName().replace('\\', '/'), entry.getSize() < 0 ? 0 : entry.getSize()));
            }
        } catch (IOException e) {
            throw new BizException("读取算子产物压缩包失败: " + e.getMessage(), e);
        }
        return out;
    }

    private static byte[] readZipEntry(Path zip, String name) {
        String entryName = name.replace('\\', '/');
        try (ZipInputStream zin = new ZipInputStream(Files.newInputStream(zip), StandardCharsets.UTF_8)) {
            ZipEntry entry;
            while ((entry = zin.getNextEntry()) != null) {
                if (!entry.isDirectory() && entry.getName().replace('\\', '/').equals(entryName)) {
                    return zin.readAllBytes();
                }
            }
        } catch (IOException e) {
            throw new BizException("读取算子产物压缩包失败: " + e.getMessage(), e);
        }
        throw new BizException("压缩包内不存在条目: " + name);
    }

    private static long sizeOf(Path file) {
        try {
            return Files.size(file);
        } catch (IOException e) {
            return 0L;
        }
    }
}
