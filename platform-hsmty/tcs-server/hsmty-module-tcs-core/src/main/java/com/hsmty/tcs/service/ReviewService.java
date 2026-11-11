package com.hsmty.tcs.service;

import com.hsmty.core.common.entity.PageResult;
import com.hsmty.tcs.pojo.dto.ReviewListDTO;
import com.hsmty.tcs.pojo.po.ReviewOrderEntity;
import com.hsmty.tcs.pojo.vo.ReviewAddResultVO;
import com.hsmty.tcs.pojo.vo.ReviewDetailVO;
import com.hsmty.tcs.pojo.vo.ReviewOrderVO;
import com.mybatisflex.core.service.IService;

import java.util.Map;

/**
 * <p>条件复核服务：条目结论（A 确认 / B 修正 / C 剔除）、整单闭环并回写数据集。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public interface ReviewService extends IService<ReviewOrderEntity> {

    /**
     * 复核单状态中文名。
     */
    Map<String, String> ORDER_STATUS_NAMES = Map.of(
            "pending", "待复核", "doing", "复核中", "done", "已闭环", "void", "已作废");

    /**
     * <p>将 Long ID 或 bizNo 解析为内部主键。
     *
     * @param reference 内部主键或业务编号
     * @return 内部主键
     */
    Long resolveId(String reference);

    /**
     * <p>分页查询复核单。
     *
     * @param dto 查询入参
     * @return 分页结果
     */
    PageResult<ReviewOrderVO> page(ReviewListDTO dto);

    /**
     * <p>查询复核单详情（含条目）。
     *
     * @param orderId 复核单内部主键
     * @return 复核单详情
     */
    ReviewDetailVO detail(Long orderId);

    /**
     * <p>将数据集条目加入复核。
     *
     * @param datasetItemId 数据集条目内部主键
     * @return 复核单摘要
     */
    ReviewAddResultVO addFromDatasetItem(Long datasetItemId);

    /**
     * <p>保存条目结论。
     *
     * @param itemId         复核条目内部主键
     * @param conclusion     A/B/C
     * @param revisedPayload B 类修正后数据行
     */
    void conclude(Long itemId, String conclusion, Map<String, Object> revisedPayload);

    /**
     * <p>撤销条目结论（闭环前）。
     *
     * @param itemId 复核条目内部主键
     */
    void unconclude(Long itemId);

    /**
     * <p>整单闭环并回写数据集。
     *
     * @param orderId 复核单内部主键
     */
    void close(Long orderId);
}
