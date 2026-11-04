package com.wbdz.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 算子进度文件读取路径兼容测试。
 *
 * @author wbdz
 * @since 2026-11-04
 */
class OperatorClientTest {

    @TempDir
    Path runtimeDir;

    @Test
    void readsProgressFromOutputsAndOutput() throws Exception {
        assertProgress("outputs", "running", 3);
        assertProgress("output", "completed", 2);
    }

    private void assertProgress(String outputDir, String status, int processed) throws Exception {
        long runId = status.equals("running") ? 101L : 102L;
        Path progressDir = runtimeDir.resolve(outputDir).resolve("_progress");
        Files.createDirectories(progressDir);
        Files.writeString(progressDir.resolve(runId + ".json"), """
                {"status":"%s","total":5,"processed":%d}
                """.formatted(status, processed), StandardCharsets.UTF_8);

        OperatorClient client = new OperatorClient(null);
        Field field = OperatorClient.class.getDeclaredField("opRuntimeDir");
        field.setAccessible(true);
        field.set(client, runtimeDir.toString());

        Map<String, Object> progress = client.readProgress(runId);
        assertThat(progress)
                .containsEntry("status", status)
                .containsEntry("total", 5)
                .containsEntry("processed", processed);
    }
}