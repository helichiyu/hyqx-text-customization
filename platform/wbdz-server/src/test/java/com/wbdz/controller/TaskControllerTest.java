package com.wbdz.controller;

import com.wbdz.common.GlobalExceptionHandler;
import com.wbdz.dto.TaskCreateDTO;
import com.wbdz.dto.TaskUpdateDTO;
import com.wbdz.service.TaskService;
import com.wbdz.vo.TaskDetailVO;
import com.wbdz.vo.TaskVO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 任务管理接口契约测试。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@ExtendWith(MockitoExtension.class)
class TaskControllerTest {

    @Mock
    private TaskService taskService;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        TaskController controller = new TaskController(taskService);
        mockMvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void createReturnsTaskVo() throws Exception {
        TaskVO task = new TaskVO();
        task.setId(9L);
        task.setName("新闻任务");
        when(taskService.create(any(TaskCreateDTO.class))).thenReturn(task);

        mockMvc.perform(post("/api/task")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":"新闻任务","line":"metadata","batchId":1,"priority":"mid","threshold":0.8}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.name").value("新闻任务"));
    }

    @Test
    void updatePassesTypedDto() throws Exception {
        when(taskService.resolveId("9")).thenReturn(9L);
        when(taskService.update(eq(9L), any(TaskUpdateDTO.class))).thenReturn(new TaskVO());

        mockMvc.perform(put("/api/task/9")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":"调整后任务","batchId":1,"priority":"high","threshold":0.75}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));

        verify(taskService).update(eq(9L), any(TaskUpdateDTO.class));
    }

    @Test
    void rejectPassesFromStage() throws Exception {
        when(taskService.resolveId("9")).thenReturn(9L);

        mockMvc.perform(post("/api/task/9/reject")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"fromStage\":2}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));

        verify(taskService).reject(9L, 2);
    }

@Test
    void detailAcceptsBizNoAndLegacyNumericReference() throws Exception {
        when(taskService.resolveId("TASK261105ABCDEF")).thenReturn(9L);
        when(taskService.resolveId("9")).thenReturn(9L);
        TaskDetailVO detail = new TaskDetailVO();
        detail.setId(9L);
        detail.setBizNo("TASK261105ABCDEF");
        when(taskService.detail(9L)).thenReturn(detail);

        mockMvc.perform(get("/api/task/by-no/TASK261105ABCDEF"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.bizNo").value("TASK261105ABCDEF"));

        mockMvc.perform(get("/api/task/9"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.bizNo").value("TASK261105ABCDEF"));
    }
    @Test
    void thresholdRejectsValueAboveOne() throws Exception {
        mockMvc.perform(put("/api/task/9/threshold")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"threshold\":1.2}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(1))
                .andExpect(jsonPath("$.msg", containsString("阈值不能大于 1")));
    }
}