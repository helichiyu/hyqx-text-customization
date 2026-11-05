package com.wbdz.service;

import com.wbdz.entity.ParamVersion;
import com.wbdz.vo.ParamLineConfigVO;
import com.wbdz.vo.ParamOverviewVO;
import com.wbdz.vo.ParamVersionVO;

import java.util.List;

/**
 * 参数配置服务。
 *
 * @author wbdz
 * @since 2026-11-05
 */
public interface ParamService {

    /** 查询产线配置页数据。 */
    ParamLineConfigVO lineConfig(String line);

    /** 查询全部产线版本概览。 */
    List<ParamOverviewVO> overview();

    /** 保存参数草稿。 */
    void saveDraft(String line, String content);

    /** 发布参数版本。 */
    ParamVersionVO publish(String line, String content);

    /** 查询最新已发布版本。 */
    ParamVersion latest(String line);

    /** v1.0 → v1.1（次版本自增）；无历史则 v1.0。 */
    static String bump(String current) {
        if (current == null || !current.matches("v\\d+\\.\\d+")) {
            return "v1.0";
        }
        int dot = current.indexOf('.');
        return "v" + current.substring(1, dot) + "." + (Integer.parseInt(current.substring(dot + 1)) + 1);
    }
}