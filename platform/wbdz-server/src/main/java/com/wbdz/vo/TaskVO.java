package com.wbdz.vo;

import com.wbdz.entity.TaskMain;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.math.BigDecimal;

/**
 * 任务基础信息。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@Schema(description = "任务基础信息")
public class TaskVO {

    @Schema(description = "内部主键，仅服务内部使用", example = "2074457061897732097")
    private Long id;

    @Schema(description = "任务业务编号", example = "TASK261026A3F9KX")
    private String bizNo;

    @Schema(description = "任务名称")
    private String name;

    @Schema(description = "产线代码", example = "metadata")
    private String line;

    @Schema(description = "产线中文名", example = "文本元信息")
    private String lineName;

    @Schema(description = "任务状态", example = "draft")
    private String status;

    @Schema(description = "任务状态中文名", example = "草稿")
    private String statusName;

    @Schema(description = "优先级：high/mid/low", example = "mid")
    private String priority;

    @Schema(description = "图文融合任务大类", example = "统计")
    private String imageClass;

    @Schema(description = "素材批次内部主键")
    private Long batchId;

    @Schema(description = "参数版本号", example = "v1.0")
    private String paramVersion;

    @Schema(description = "任务级置信度阈值", example = "0.8")
    private BigDecimal threshold;

    @Schema(description = "当前执行环节号，0 表示未开始", example = "1")
    private Integer currentStage;

    @Schema(description = "创建人")
    private String createBy;

    @Schema(description = "创建时间")
    private String createTime;

    /**
     * 从任务实体创建基础 VO，不复制逻辑删除和审计敏感字段。
     *
     * @param task 任务实体
     * @return 任务 VO
     */
    public static TaskVO from(TaskMain task) {
        TaskVO vo = new TaskVO();
        vo.setId(task.getId());
        vo.setBizNo(task.getBizNo());
        vo.setName(task.getName());
        vo.setLine(task.getLine());
        vo.setStatus(task.getStatus());
        vo.setPriority(task.getPriority());
        vo.setImageClass(task.getImageClass());
        vo.setBatchId(task.getBatchId());
        vo.setParamVersion(task.getParamVersion());
        vo.setThreshold(task.getThreshold());
        vo.setCurrentStage(task.getCurrentStage());
        vo.setCreateBy(task.getCreateBy());
        vo.setCreateTime(String.valueOf(task.getCreateTime()));
        return vo;
    }
}