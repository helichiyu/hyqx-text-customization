package com.wbdz.service;

import com.wbdz.common.PageResult;
import com.wbdz.vo.ReviewAddResultVO;
import com.wbdz.vo.ReviewDetailVO;
import com.wbdz.vo.ReviewOrderVO;

import java.util.Map;

/**
 * 条件复核服务。
 *
 * @author wbdz
 * @since 2026-11-05
 */
public interface ReviewService {

    /** 复核单状态中文名。 */
    Map<String, String> ORDER_STATUS_NAMES = Map.of(
            "pending", "待复核", "doing", "复核中", "done", "已闭环", "void", "已作废");

    /** 分页查询复核单。 */
    PageResult<ReviewOrderVO> page(String status, String line, Long taskId, int pageNum, int pageSize);

    /** 查询复核单详情。 */
    ReviewDetailVO detail(Long orderId);

    /** 将数据集条目加入复核。 */
    ReviewAddResultVO addFromDatasetItem(Long datasetItemId);

    /** 保存条目结论。 */
    void conclude(Long itemId, String conclusion, Map<String, Object> revisedPayload);

    /** 撤销条目结论。 */
    void unconclude(Long itemId);

    /** 闭环复核单。 */
    void close(Long orderId);
}