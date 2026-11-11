package com.hsmty.tcs.service;

import com.hsmty.core.common.entity.PageResult;
import com.hsmty.tcs.pojo.dto.MaterialEditDTO;
import com.hsmty.tcs.pojo.dto.MaterialListDTO;
import com.hsmty.tcs.pojo.po.MatBatchEntity;
import com.hsmty.tcs.pojo.vo.MaterialDetailVO;
import com.hsmty.tcs.pojo.vo.MaterialRowVO;
import com.hsmty.tcs.pojo.vo.MaterialVO;
import com.mybatisflex.core.service.IService;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * <p>素材服务：上传、准入校验、状态机、编辑与删除、变更记录。
 *
 * @author helichiyu
 * @since 2.0.1
 */
public interface MaterialService extends IService<MatBatchEntity> {

    /**
     * <p>将 Long ID 或 bizNo 解析为内部主键。
     *
     * @param reference 内部主键或业务编号
     * @return 内部主键
     */
    Long resolveId(String reference);

    /**
     * <p>上传并完成文件级校验。
     *
     * @param line  产线代码
     * @param name  批次名称
     * @param files 上传文件
     * @return 素材批次
     */
    MaterialVO upload(String line, String name, List<MultipartFile> files);

    /**
     * <p>执行准入校验。
     *
     * @param batchId 批次内部主键
     * @return 素材批次
     */
    MaterialVO check(Long batchId);

    /**
     * <p>移交素材批次。
     *
     * @param batchId 批次内部主键
     * @return 素材批次
     */
    MaterialVO release(Long batchId);

    /**
     * <p>编辑素材批次基本信息。
     *
     * @param batchId 批次内部主键
     * @param dto     编辑入参
     * @return 素材批次
     */
    MaterialVO edit(Long batchId, MaterialEditDTO dto);

    /**
     * <p>删除素材批次。
     *
     * @param batchId 批次内部主键
     */
    void remove(Long batchId);

    /**
     * <p>分页查询素材批次。
     *
     * @param dto 查询入参
     * @return 分页结果
     */
    PageResult<MaterialRowVO> page(MaterialListDTO dto);

    /**
     * <p>查询素材批次详情。
     *
     * @param batchId 批次内部主键
     * @return 批次详情
     */
    MaterialDetailVO detail(Long batchId);

    /**
     * <p>查询关联的非草稿任务。
     *
     * @param batchId 批次内部主键
     * @return 任务内部主键列表
     */
    List<Long> linkedTaskIds(Long batchId);
}
