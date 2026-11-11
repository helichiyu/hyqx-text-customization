package com.hsmty.tcs.service;

import com.hsmty.tcs.pojo.po.ParamVersionEntity;
import com.hsmty.tcs.pojo.vo.ParamLineConfigVO;
import com.hsmty.tcs.pojo.vo.ParamOverviewVO;
import com.hsmty.tcs.pojo.vo.ParamVersionVO;
import com.mybatisflex.core.service.IService;

import java.util.List;

/**
 * <p>参数配置服务：草稿保存 / 发布版本；任务创建时锁定参数快照。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public interface ParamService extends IService<ParamVersionEntity> {

    /**
     * <p>查询产线配置页数据。
     *
     * @param line 产线代码或 common
     * @return 配置页数据
     */
    ParamLineConfigVO lineConfig(String line);

    /**
     * <p>查询全部产线最新版本概览。
     *
     * @return 概览列表
     */
    List<ParamOverviewVO> overview();

    /**
     * <p>保存参数草稿（覆盖式）。
     *
     * @param line    产线代码或 common
     * @param content 参数组 JSON
     */
    void saveDraft(String line, String content);

    /**
     * <p>发布参数版本（版本号自增，草稿清除）。
     *
     * @param line    产线代码或 common
     * @param content 参数组 JSON；为空时取草稿
     * @return 新版本
     */
    ParamVersionVO publish(String line, String content);

    /**
     * <p>查询最新已发布版本。
     *
     * @param line 产线代码
     * @return 最新版本；无发布记录时为 null
     */
    ParamVersionEntity latest(String line);

    /**
     * <p>v1.0 → v1.1（次版本自增）；无历史则 v1.0。
     *
     * @param current 当前版本号
     * @return 下一版本号
     */
    static String bump(String current) {
        if (current == null || !current.matches("v\\d+\\.\\d+")) {
            return "v1.0";
        }
        int dot = current.indexOf('.');
        return "v" + current.substring(1, dot) + "." + (Integer.parseInt(current.substring(dot + 1)) + 1);
    }
}
