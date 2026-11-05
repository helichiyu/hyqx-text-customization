package com.wbdz.controller;

import com.mybatisflex.core.query.QueryWrapper;
import com.wbdz.common.ApiResult;
import com.wbdz.common.BizException;
import com.wbdz.entity.TaskStageRun;
import com.wbdz.mapper.TaskStageRunMapper;
import com.wbdz.service.OperatorClient;
import com.wbdz.vo.ArtifactFileVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

import static com.wbdz.entity.table.TaskStageRunTableDef.TASK_STAGE_RUN;

/**
 * 算子产物文件代理：列出/下载环节输出目录内文件（复核工作台可视化、血缘回溯用）。
 *
 * <p>安全：只允许访问指定环节输出目录之内的路径（规范化后前缀校验，防目录穿越）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Slf4j
@Tag(name = "产物文件", description = "算子环节产物文件列表和预览")
@RestController
@RequestMapping("/api/artifact")
@RequiredArgsConstructor
public class ArtifactController {

    private final TaskStageRunMapper stageRunMapper;

    private final OperatorClient operatorClient;

    /** 环节输出目录内文件清单（递归，相对路径 + 大小）。 */
    @Operation(summary = "查询环节产物文件列表")
    @GetMapping("/list")
    public ApiResult<List<ArtifactFileVO>> list(@RequestParam Long runId) {
        Path dir = runDir(runId);
        List<ArtifactFileVO> out = new ArrayList<>();
        try (Stream<Path> walk = Files.walk(dir)) {
            walk.filter(Files::isRegularFile).forEach(path -> {
                long size = 0;
                try {
                    size = Files.size(path);
                } catch (IOException e) {
                    log.warn("读取产物文件大小失败: path={} err={}", path, e.getMessage());
                }
                out.add(new ArtifactFileVO(dir.relativize(path).toString().replace('\\', '/'), size));
            });
        } catch (IOException e) {
            throw new BizException("读取输出目录失败: " + e.getMessage());
        }
        out.sort((a, b) -> a.name().compareTo(b.name()));
        return ApiResult.success(out);
    }

    /** 读取/下载环节输出目录内文件（download=true 附件）。 */
    @Operation(summary = "读取或下载环节产物文件")
    @GetMapping("/file")
    public ResponseEntity<byte[]> file(@RequestParam Long runId,
                                       @RequestParam String name,
                                       @RequestParam(required = false, defaultValue = "false") boolean download) {
        Path dir = runDir(runId);
        Path target = dir.resolve(name).normalize();
        if (!target.startsWith(dir.normalize())) {
            throw new BizException("路径越界（仅允许环节输出目录之内）");
        }
        if (!Files.isRegularFile(target)) {
            throw new BizException("文件不存在: " + name);
        }
        try {
            byte[] bytes = Files.readAllBytes(target);
            MediaType type = mediaType(name);
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(type);
            if (download) {
                headers.setContentDisposition(ContentDisposition.attachment()
                        .filename(target.getFileName().toString(), StandardCharsets.UTF_8).build());
            }
            return new ResponseEntity<>(bytes, headers, org.springframework.http.HttpStatus.OK);
        } catch (IOException e) {
            throw new BizException("读取文件失败: " + e.getMessage());
        }
    }

    private Path runDir(Long runId) {
        TaskStageRun run = stageRunMapper.selectOneByQuery(QueryWrapper.create()
                .where(TASK_STAGE_RUN.ID.eq(runId)));
        if (run == null || run.getOutputPath() == null) {
            throw new BizException("环节执行记录不存在或尚无输出");
        }
        Path dir = operatorClient.toHostPath(run.getOutputPath());
        // outputFile 可能是目录（中段）或阶段 zip（末位）。zip 可能在运行目录内，
        // 也可能被放在 output 根下（如逐页检测）：优先按时间戳匹配同名运行目录。
        if (!Files.isDirectory(dir)) {
            Path zip = dir;
            String zipName = zip.getFileName().toString();
            String token = zipName.replaceFirst("^run_", "").replaceFirst("_stage_output\\.zip$", "");
            Path parent = zip.getParent();
            Path runDir = null;
            if (parent != null && Files.isDirectory(parent)) {
                try (Stream<Path> children = Files.list(parent)) {
                    runDir = children
                            .filter(Files::isDirectory)
                            .filter(path -> !token.equals(zipName) && path.getFileName().toString().endsWith(token))
                            .findFirst().orElse(null);
                } catch (IOException e) {
                    log.warn("匹配环节运行目录失败: zip={} err={}", zip, e.getMessage());
                }
            }
            dir = runDir != null ? runDir : parent;
        }
        if (dir == null || !Files.isDirectory(dir)) {
            throw new BizException("输出目录不存在（可能已被清理）");
        }
        return dir.normalize();
    }

    private static MediaType mediaType(String name) {
        String lower = name.toLowerCase();
        if (lower.endsWith(".png")) {
            return MediaType.IMAGE_PNG;
        }
        if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
            return MediaType.IMAGE_JPEG;
        }
        if (lower.endsWith(".gif")) {
            return MediaType.IMAGE_GIF;
        }
        if (lower.endsWith(".json") || lower.endsWith(".jsonl") || lower.endsWith(".txt")
                || lower.endsWith(".md")) {
            return MediaType.TEXT_PLAIN;
        }
        return MediaType.APPLICATION_OCTET_STREAM;
    }
}