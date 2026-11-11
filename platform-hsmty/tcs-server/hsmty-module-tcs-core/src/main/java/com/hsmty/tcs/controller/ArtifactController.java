package com.hsmty.tcs.controller;

import com.hsmty.core.common.entity.ApiResult;
import com.hsmty.tcs.pojo.vo.ArtifactFileVO;
import com.hsmty.tcs.service.ArtifactService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * <p>算子产物文件代理：列出/下载环节输出文件（复核工作台可视化、血缘回溯用）。
 *
 * <p>产物文件由算子通过文件接口提供，平台不直接访问算子本地目录。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Tag(name = "产物文件", description = "算子环节产物文件列表和预览")
@RestController
@RequestMapping("artifact")
@RequiredArgsConstructor
public class ArtifactController {

    private final ArtifactService artifactService;

    /**
     * <p>环节输出目录内文件清单（相对路径 + 大小）。
     */
    @Operation(summary = "查询环节产物文件列表")
    @PreAuthorize("hasAnyAuthority('tcs:artifact:detail')")
    @GetMapping("/list")
    public ApiResult<List<ArtifactFileVO>> list(@RequestParam Long runId) {
        return ApiResult.success(artifactService.list(runId));
    }

    /**
     * <p>读取/下载环节输出目录内文件。
     */
    @Operation(summary = "读取或下载环节产物文件")
    @PreAuthorize("hasAnyAuthority('tcs:artifact:detail')")
    @GetMapping("/file")
    public ResponseEntity<byte[]> file(@RequestParam Long runId,
                                       @RequestParam String name,
                                       @RequestParam(required = false, defaultValue = "false") boolean download) {
        byte[] bytes = artifactService.read(runId, name);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(mediaType(name));
        if (download) {
            headers.setContentDisposition(ContentDisposition.attachment()
                    .filename(name.substring(name.lastIndexOf('/') + 1), StandardCharsets.UTF_8).build());
        }
        return new ResponseEntity<>(bytes, headers, org.springframework.http.HttpStatus.OK);
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
