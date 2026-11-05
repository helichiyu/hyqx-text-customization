package com.wbdz.vo;

import com.wbdz.common.JsonUtil;
import com.wbdz.entity.ParamVersion;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 参数版本。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@Data
@Schema(description = "参数版本")
public class ParamVersionVO {
    @Schema(description = "产线代码")
    private String line;
    @Schema(description = "参数版本号")
    private String version;
    @Schema(description = "参数组")
    private List<Map<String, Object>> content;
    @Schema(description = "发布时间")
    private String publishedAt;
    @Schema(description = "发布人")
    private String publishedBy;

    public static ParamVersionVO from(ParamVersion version) {
        if (version == null) {
            return null;
        }
        ParamVersionVO vo = new ParamVersionVO();
        vo.setLine(version.getLine());
        vo.setVersion(version.getVersion());
        vo.setContent(version.getContent() == null ? List.of() : JsonUtil.readList(version.getContent()));
        vo.setPublishedAt(String.valueOf(version.getPublishedAt()));
        vo.setPublishedBy(version.getPublishedBy());
        return vo;
    }
}