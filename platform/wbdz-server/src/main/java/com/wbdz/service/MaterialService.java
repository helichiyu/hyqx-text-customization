package com.wbdz.service;

import com.wbdz.common.PageResult;
import com.wbdz.vo.MaterialDetailVO;
import com.wbdz.vo.MaterialRowVO;
import com.wbdz.vo.MaterialVO;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * 素材服务。
 *
 * @author wbdz
 * @since 2026-11-05
 */
public interface MaterialService {

    /** 将 Long ID 或 bizNo 解析为内部主键。 */
    Long resolveId(String reference);

    /** 上传并完成文件级校验。 */
    MaterialVO upload(String line, String name, List<MultipartFile> files);

    /** 执行准入校验。 */
    MaterialVO check(Long batchId);

    /** 移交素材批次。 */
    MaterialVO release(Long batchId);

    /** 编辑素材批次。 */
    MaterialVO edit(Long batchId, String newName, String newLine);

    /** 删除素材批次。 */
    void delete(Long batchId);

    /** 分页查询素材批次。 */
    PageResult<MaterialRowVO> page(String line, String name, String status, int pageNum, int pageSize);

    /** 查询素材批次详情。 */
    MaterialDetailVO detail(Long batchId);

    /** 查询关联的非草稿任务。 */
    List<Long> linkedTaskIds(Long batchId);
}