package com.hsmty.tcs.service;

import com.hsmty.core.common.entity.PageResult;
import com.hsmty.tcs.pojo.dto.DatasetDetailDTO;
import com.hsmty.tcs.pojo.dto.DatasetListDTO;
import com.hsmty.tcs.pojo.dto.DeliveryListDTO;
import com.hsmty.tcs.pojo.po.DatasetEntity;
import com.hsmty.tcs.pojo.vo.DatasetDeliveryRowVO;
import com.hsmty.tcs.pojo.vo.DatasetDetailVO;
import com.hsmty.tcs.pojo.vo.DatasetVO;
import com.mybatisflex.core.service.IService;

import java.util.Map;

/**
 * <p>数据集服务：候选 → 发布 → 回滚，质检报告下载与交付记录。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public interface DatasetService extends IService<DatasetEntity> {

    /**
     * 数据集状态中文名。
     */
    Map<String, String> STATUS_NAMES = Map.of(
            "candidate", "候选", "published", "已发布", "rolledback", "已回滚");

    /**
     * <p>将 Long ID 或 bizNo 解析为内部主键。
     *
     * @param reference 内部主键或业务编号
     * @return 内部主键
     */
    Long resolveId(String reference);

    /**
     * <p>分页查询数据集。
     *
     * @param dto 查询入参
     * @return 分页结果
     */
    PageResult<DatasetVO> page(DatasetListDTO dto);

    /**
     * <p>查询数据集详情（含明细分页、交付与回滚记录）。
     *
     * @param id  数据集内部主键
     * @param dto 明细查询入参
     * @return 数据集详情
     */
    DatasetDetailVO detail(Long id, DatasetDetailDTO dto);

    /**
     * <p>发布数据集。
     *
     * @param id 数据集内部主键
     * @return 数据集
     */
    DatasetVO publish(Long id);

    /**
     * <p>回滚数据集。
     *
     * @param id     数据集内部主键
     * @param reason 回滚原因
     * @return 数据集
     */
    DatasetVO rollback(Long id, String reason);

    /**
     * <p>删除数据集（逻辑删除，级联删除条目）；已发布数据集须先回滚。
     *
     * @param id 数据集内部主键
     */
    void remove(Long id);

    /**
     * <p>生成质量报告并记录交付。
     *
     * @param id 数据集内部主键
     * @return 报告文件
     */
    ReportFile report(Long id);

    /**
     * <p>分页查询交付记录。
     *
     * @param dto 查询入参
     * @return 分页结果
     */
    PageResult<DatasetDeliveryRowVO> deliveries(DeliveryListDTO dto);

    /**
     * 报告文件（文件名 + 字节）。
     *
     * @param filename 文件名
     * @param bytes    文件内容
     */
    record ReportFile(String filename, byte[] bytes) {
    }
}
