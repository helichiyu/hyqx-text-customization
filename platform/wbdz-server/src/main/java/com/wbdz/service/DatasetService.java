package com.wbdz.service;

import com.wbdz.common.PageResult;
import com.wbdz.vo.DatasetDeliveryRowVO;
import com.wbdz.vo.DatasetDetailVO;
import com.wbdz.vo.DatasetVO;

import java.util.Map;

/**
 * 数据集服务。
 *
 * @author wbdz
 * @since 2026-11-05
 */
public interface DatasetService {

    /** 数据集状态中文名。 */
    Map<String, String> STATUS_NAMES = Map.of(
            "candidate", "候选", "published", "已发布", "rolledback", "已回滚");

    /** 分页查询数据集。 */
    PageResult<DatasetVO> page(String line, String status, String keyword, int pageNum, int pageSize);

    /** 查询数据集详情。 */
    DatasetDetailVO detail(Long id, String reviewStatus, int pageNum, int pageSize);

    /** 发布数据集。 */
    DatasetVO publish(Long id);

    /** 回滚数据集。 */
    DatasetVO rollback(Long id, String reason);

    /** 生成质量报告并记录交付。 */
    ReportFile report(Long id);

    /** 分页查询交付记录。 */
    PageResult<DatasetDeliveryRowVO> deliveries(int pageNum, int pageSize);

    /** 报告文件（文件名 + 字节）。 */
    record ReportFile(String filename, byte[] bytes) {
    }
}