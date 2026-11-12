package com.hsmty.tcs.service.impl;

import com.hsmty.core.common.entity.PageResult;
import com.hsmty.core.util.BeanCopyUtils;
import com.hsmty.core.util.JsonUtils;
import com.hsmty.core.util.PageUtils;
import com.hsmty.tcs.common.AuthContext;
import com.hsmty.tcs.common.BizException;
import com.hsmty.tcs.common.BizId;
import com.hsmty.tcs.common.Times;
import com.hsmty.tcs.mapper.MatBatchMapper;
import com.hsmty.tcs.mapper.MatChangeLogMapper;
import com.hsmty.tcs.mapper.MatFileMapper;
import com.hsmty.tcs.mapper.ParamVersionMapper;
import com.hsmty.tcs.mapper.TaskMainMapper;
import com.hsmty.tcs.operator.LineRegistry;
import com.hsmty.tcs.pojo.dto.MaterialEditDTO;
import com.hsmty.tcs.pojo.dto.MaterialListDTO;
import com.hsmty.tcs.pojo.po.MatBatchEntity;
import com.hsmty.tcs.pojo.po.MatChangeLogEntity;
import com.hsmty.tcs.pojo.po.MatFileEntity;
import com.hsmty.tcs.pojo.po.ParamVersionEntity;
import com.hsmty.tcs.pojo.po.TaskMainEntity;
import com.hsmty.tcs.pojo.vo.MaterialDetailVO;
import com.hsmty.tcs.pojo.vo.MaterialRowVO;
import com.hsmty.tcs.pojo.vo.MaterialVO;
import com.hsmty.tcs.service.MaterialService;
import com.mybatisflex.core.paginate.Page;
import com.mybatisflex.core.query.QueryWrapper;
import com.mybatisflex.spring.service.impl.ServiceImpl;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.Jsoup;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.core.type.TypeReference;

import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * <p>素材管理实现。
 *
 * <p>口径对齐《素材管理·研发对齐 v2》：白名单按产线固定、剔除不阻断、
 * 剔除后有效条数为 0 → 上传失败（只能删除重传）、已移交/已关联不可删。
 *
 * @author helichiyu
 * @since 2.0.1
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MaterialServiceImpl extends ServiceImpl<MatBatchMapper, MatBatchEntity> implements MaterialService {

    private static final TypeReference<List<Map<String, Object>>> GROUP_LIST =
            new TypeReference<List<Map<String, Object>>>() {
            };

    private final MatBatchMapper batchMapper;

    private final MatFileMapper fileMapper;

    private final MatChangeLogMapper changeLogMapper;

    private final TaskMainMapper taskMapper;

    private final ParamVersionMapper paramVersionMapper;

    @Value("${tcs.storage-dir:./data}")
    private String storageDir;

    /**
     * 单个源文件（ZIP 解包后统一形态）。
     */
    private record SrcFile(String name, String ext, byte[] data) {
    }

    // ==================== 上传 ====================

    /**
     * 上传素材批次：接收文件（含 ZIP 解包），落盘并完成文件级校验，批次置「未校验」。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public MaterialVO upload(String line, String name, List<MultipartFile> files) {
        require(LineRegistry.LINE_NAMES.containsKey(line), "产线不存在");
        require(name != null && !name.isBlank(), "请填写素材批次名称");
        require(files != null && !files.isEmpty(), "请至少选择一个文件");
        // 批次名称同产线唯一（含上传失败批次）
        Long dup = batchMapper.selectCountByQuery(QueryWrapper.create()
                .where("line = ?", line).and("name = ?", name.trim()));
        require(dup == null || dup == 0, "批次名称与同产线已有批次重复");

        MatBatchEntity batch = new MatBatchEntity();
        String prefix = LineRegistry.LINE_PREFIX.get(line);
        batch.setBizNo(BizId.nextUnique(prefix, candidate -> batchMapper.selectCountByQuery(
                QueryWrapper.create().where("biz_no = ?", candidate)) > 0));
        batch.setName(name.trim());
        batch.setLine(line);
        batch.setStatus("uncheked");
        batch.setFileCount(0);
        batch.setTotalCount(0);
        batch.setCreateBy(AuthContext.username());
        batchMapper.insert(batch);

        List<SrcFile> srcFiles = new ArrayList<>();
        for (MultipartFile f : files) {
            if ("zip".equals(ext(f.getOriginalFilename()))) {
                srcFiles.addAll(unzip(f));
            } else {
                srcFiles.add(new SrcFile(sanitize(f.getOriginalFilename()),
                        ext(f.getOriginalFilename()), readAll(f)));
            }
        }

        Path dir = Path.of(storageDir, "materials", String.valueOf(batch.getId()));
        List<MatFileEntity> rows = new ArrayList<>();
        Set<String> seenHash = new HashSet<>();
        for (int i = 0; i < srcFiles.size(); i++) {
            SrcFile src = srcFiles.get(i);
            MatFileEntity row = new MatFileEntity();
            row.setBatchId(batch.getId());
            row.setName(src.name());
            row.setExt(src.ext());
            row.setSizeBytes((long) src.data().length);
            row.setSha256(sha256(src.data()));
            String reject = checkFile(line, src);
            if (reject == null && !seenHash.add(row.getSha256())) {
                reject = "重复文件（同批次哈希一致）";
            }
            row.setStatus(reject == null ? "passed" : "rejected");
            row.setRejectReason(reject);
            if (reject == null) {
                if (byPage(line) && "pdf".equals(src.ext())) {
                    try {
                        row.setPageCount(pdfPages(src.data()));
                    } catch (IOException e) {
                        row.setStatus("rejected");
                        row.setRejectReason("PDF 加密或损坏，无法解析");
                        rows.add(row);
                        continue;
                    }
                }
                saveTo(dir, i + 1, src, row);
            }
            rows.add(row);
        }
        rows.forEach(fileMapper::insert);
        summarize(batch, rows);
        return toVO(batch);
    }

    private void saveTo(Path dir, int idx, SrcFile src, MatFileEntity row) {
        try {
            Files.createDirectories(dir);
            String rel = "materials/" + row.getBatchId() + "/" + idx + "_" + src.name();
            Files.copy(new ByteArrayInputStream(src.data()), Path.of(storageDir, rel),
                    StandardCopyOption.REPLACE_EXISTING);
            row.setStorePath(rel);
        } catch (IOException e) {
            log.error("素材落盘失败: {}", e.getMessage(), e);
            throw new BizException("素材保存失败：" + src.name());
        }
    }

    /**
     * 逐文件准入校验；返回 null 表示通过，否则返回剔除原因（中文）。
     */
    private String checkFile(String line, SrcFile src) {
        List<String> whitelist = LineRegistry.LINE_WHITELIST.get(line);
        if (!whitelist.contains(src.ext())) {
            return "格式不在本产线白名单（" + String.join("/", whitelist) + "）";
        }
        long limitBytes = admissionLong("单文件大小上限(MB)", 50L) * 1024 * 1024;
        if (src.data().length > limitBytes) {
            return "单文件超过大小上限（" + (limitBytes / 1024 / 1024) + "MB）";
        }
        return switch (line) {
            case "formula", "layout" -> checkPdf(src);
            case "graphic" -> checkImage(src);
            case "metadata" -> checkHtml(src);
            default -> null;
        };
    }

    private String checkPdf(SrcFile src) {
        try {
            if (pdfPages(src.data()) <= 0) {
                return "PDF 页数为 0";
            }
            return null;
        } catch (Exception e) {
            log.debug("PDF 准入解析失败", e);
            return "PDF 加密或损坏，无法解析";
        }
    }

    /**
     * PDFBox 解析页数；加密/损坏会抛异常。
     */
    private static int pdfPages(byte[] data) throws IOException {
        try (var doc = org.apache.pdfbox.Loader.loadPDF(
                new org.apache.pdfbox.io.RandomAccessReadBuffer(data))) {
            return doc.getNumberOfPages();
        }
    }

    private String checkImage(SrcFile src) {
        try (ImageInputStream in = ImageIO.createImageInputStream(new ByteArrayInputStream(src.data()))) {
            Iterator<ImageReader> readers = ImageIO.getImageReaders(in);
            if (!readers.hasNext()) {
                return "图片无法解码";
            }
            ImageReader reader = readers.next();
            try {
                reader.setInput(in);
                long min = admissionLong("图片最小分辨率", 600L);
                if (reader.getWidth(0) < min || reader.getHeight(0) < min) {
                    return "分辨率低于最小要求（" + min + "×" + min + "）";
                }
                return null;
            } finally {
                reader.dispose();
            }
        } catch (Exception e) {
            log.debug("图片准入解码失败", e);
            return "图片无法解码";
        }
    }

    private String checkHtml(SrcFile src) {
        String text = decodeAuto(src.data());
        if (text == null) {
            return "编码无法识别（支持 UTF-8/GBK/GB18030）";
        }
        if (Jsoup.parse(text).text().trim().length() < 20) {
            return "去标签后可读字符不足 20";
        }
        return null;
    }

    /**
     * 素材准入规则取值（common 参数版本最新值），未配置或解析失败用默认。
     */
    private long admissionLong(String name, long dft) {
        try {
            ParamVersionEntity v = paramVersionMapper.selectOneByQuery(QueryWrapper.create()
                    .where("line = ?", "common")
                    .orderBy("published_at desc").limit(1));
            if (v != null) {
                for (Map<String, Object> g : JsonUtils.parseArray(v.getContent(), GROUP_LIST)) {
                    if (name.equals(g.get("name"))) {
                        return Long.parseLong(String.valueOf(g.get("value")).trim());
                    }
                }
            }
        } catch (Exception e) {
            log.warn("素材准入规则读取失败，使用默认值: name={} default={}", name, dft, e);
        }
        return dft;
    }

    /**
     * ZIP 解包：目录跳过、嵌套 ZIP 整批拒绝、损坏/加密整批拒绝，其余条目全部产出（白名单外按剔除计数）。
     */
    private List<SrcFile> unzip(MultipartFile zipFile) {
        List<SrcFile> out = new ArrayList<>();
        try (ZipInputStream zin = new ZipInputStream(zipFile.getInputStream(), Charset.forName("GBK"))) {
            ZipEntry entry;
            while ((entry = zin.getNextEntry()) != null) {
                if (entry.isDirectory()) {
                    continue;
                }
                String entryName = sanitize(entry.getName());
                if ("zip".equals(ext(entryName))) {
                    throw new BizException("ZIP 内含嵌套 ZIP，整批拒绝");
                }
                out.add(new SrcFile(entryName, ext(entryName), zin.readAllBytes()));
            }
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.warn("ZIP 解包失败: {}", e.getMessage());
            throw new BizException("ZIP 损坏或加密，整批拒绝");
        }
        if (out.isEmpty()) {
            throw new BizException("ZIP 内没有文件");
        }
        return out;
    }

    /**
     * 汇总批次素材条数（公式/版面 PDF 按页计）与剔除情况。
     */
    private void summarize(MatBatchEntity batch, List<MatFileEntity> rows) {
        int valid = 0;
        Map<String, Integer> reject = new LinkedHashMap<>();
        boolean byPage = byPage(batch.getLine());
        for (MatFileEntity r : rows) {
            if ("passed".equals(r.getStatus())) {
                valid += byPage && r.getPageCount() != null ? r.getPageCount() : 1;
            } else {
                reject.merge(r.getRejectReason(), 1, Integer::sum);
            }
        }
        batch.setTotalCount(rows.size());
        batch.setFileCount(valid);
        batch.setRejectSummary(reject.isEmpty() ? "[]" : JsonUtils.toJsonString(reject.entrySet().stream()
                .map(e -> Map.of("reason", e.getKey(), "count", e.getValue())).toList()));
        batchMapper.update(batch);
    }

    // ==================== 状态机 ====================

    /**
     * 准入校验：对已落盘文件重算规则并流转状态——有效条数 &gt; 0 → 已校验，否则 → 上传失败。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public MaterialVO check(Long batchId) {
        MatBatchEntity batch = batchMapper.selectOneById(batchId);
        require(batch != null, "批次不存在");
        require("uncheked".equals(batch.getStatus()), "仅「未校验」批次可做准入校验");

        List<MatFileEntity> rows = fileMapper.selectListByQuery(QueryWrapper.create()
                .where("batch_id = ?", batchId));
        for (MatFileEntity row : rows) {
            // 只有已落盘的文件重算（剔除文件未落盘，维持原结论）
            if (!"passed".equals(row.getStatus()) || row.getStorePath() == null) {
                continue;
            }
            try {
                byte[] data = Files.readAllBytes(Path.of(storageDir, row.getStorePath()));
                SrcFile src = new SrcFile(row.getName(), row.getExt(), data);
                String reject = checkFile(batch.getLine(), src);
                if (reject == null && byPage(batch.getLine()) && "pdf".equals(row.getExt())) {
                    row.setPageCount(pdfPages(data));
                }
                if (reject != null) {
                    row.setStatus("rejected");
                    row.setRejectReason(reject);
                    log.info("准入校验剔除: batch={} file={} reason={}", batchId, row.getName(), reject);
                }
            } catch (IOException e) {
                log.error("读取素材失败: {}", row.getStorePath(), e);
                row.setStatus("rejected");
                row.setRejectReason("平台存储文件读取失败");
            }
            fileMapper.update(row);
        }
        summarize(batch, rows);
        long passed = rows.stream().filter(r -> "passed".equals(r.getStatus())).count();
        batch.setStatus(passed > 0 ? "checked" : "upload_failed");
        batchMapper.update(batch);
        return toVO(batch);
    }

    /**
     * 移交：已校验 → 已移交。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public MaterialVO release(Long batchId) {
        MatBatchEntity batch = batchMapper.selectOneById(batchId);
        require(batch != null, "批次不存在");
        require("checked".equals(batch.getStatus()), "仅「已校验」批次可移交");
        batch.setStatus("released");
        batchMapper.update(batch);
        return toVO(batch);
    }

    /**
     * 编辑基本信息（仅名称/产线），写变更记录。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public MaterialVO edit(Long batchId, MaterialEditDTO dto) {
        MatBatchEntity batch = batchMapper.selectOneById(batchId);
        require(batch != null, "批次不存在");
        require(!"upload_failed".equals(batch.getStatus()), "上传失败批次不可编辑，请删除后重新上传");
        String newName = dto.name();
        String newLine = dto.line();
        if (newName != null && !newName.isBlank() && !newName.trim().equals(batch.getName())) {
            Long dup = batchMapper.selectCountByQuery(QueryWrapper.create()
                    .where("line = ?", batch.getLine()).and("name = ?", newName.trim())
                    .and("id <> ?", batchId));
            require(dup == null || dup == 0, "批次名称与同产线已有批次重复");
            logChange(batchId, "name", batch.getName(), newName.trim());
            batch.setName(newName.trim());
        }
        if (newLine != null && !newLine.isBlank() && !newLine.equals(batch.getLine())) {
            require(LineRegistry.LINE_NAMES.containsKey(newLine), "产线不存在");
            require(linkedTaskIds(batchId).isEmpty(), "批次已被任务引用，不可修改产线");
            List<String> target = LineRegistry.LINE_WHITELIST.get(newLine);
            Long bad = fileMapper.selectCountByQuery(QueryWrapper.create()
                    .where("batch_id = ?", batchId).and("status = ?", "passed")
                    .and("ext not in (" + placeholders(target.size()) + ")", target.toArray()));
            require(bad == null || bad == 0, "批次内存在不符合目标产线白名单的文件");
            logChange(batchId, "line", batch.getLine(), newLine);
            batch.setLine(newLine);
        }
        batchMapper.update(batch);
        return toVO(batch);
    }

    /**
     * 删除：任一批次状态均可删，但必须未被任务引用（任务删除后即解除引用）；
     * 明细、变更记录一并逻辑删除，并清理已落盘的素材文件。
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void remove(Long batchId) {
        MatBatchEntity batch = batchMapper.selectOneById(batchId);
        require(batch != null, "批次不存在");
        require(linkedTaskIds(batchId).isEmpty(), "批次已被任务引用，不可删除");
        List<MatFileEntity> files = fileMapper.selectListByQuery(
                QueryWrapper.create().where("batch_id = ?", batchId));
        batchMapper.deleteById(batchId);
        fileMapper.deleteByQuery(QueryWrapper.create().where("batch_id = ?", batchId));
        changeLogMapper.deleteByQuery(QueryWrapper.create().where("batch_id = ?", batchId));
        files.forEach(file -> deleteStoredFile(file.getStorePath()));
    }

    /**
     * 尽力删除落盘文件；失败只记日志，不影响删除结果。
     */
    private void deleteStoredFile(String storePath) {
        if (storePath == null || storePath.isBlank()) {
            return;
        }
        try {
            Files.deleteIfExists(Path.of(storageDir, storePath));
        } catch (Exception e) {
            log.warn("素材文件删除失败（忽略）: {} {}", storePath, e.getMessage());
        }
    }

    @Override
    public Long resolveId(String reference) {
        String ref = reference == null ? "" : reference.trim();
        if (ref.matches("\\d+")) {
            try {
                return Long.valueOf(ref);
            } catch (NumberFormatException e) {
                throw new BizException("素材批次引用格式错误", e);
            }
        }
        MatBatchEntity batch = batchMapper.selectOneByQuery(QueryWrapper.create()
                .where("biz_no = ?", ref));
        if (batch == null) {
            throw new BizException("批次不存在");
        }
        return batch.getId();
    }

    // ==================== 查询 ====================

    @Override
    public PageResult<MaterialRowVO> page(MaterialListDTO dto) {
        QueryWrapper qw = QueryWrapper.create();
        if (dto.getLine() != null && !dto.getLine().isBlank()) {
            qw.and("line = ?", dto.getLine());
        }
        if (dto.getName() != null && !dto.getName().isBlank()) {
            qw.and("name like ?", "%" + dto.getName().trim() + "%");
        }
        if (dto.getStatus() != null && !dto.getStatus().isBlank()) {
            qw.and("status = ?", dto.getStatus());
        }
        qw.orderBy("create_time desc");
        Page<MatBatchEntity> page = batchMapper.paginate(PageUtils.getPage(dto), qw);
        return PageUtils.getPageResult(page.map(this::toRowVO));
    }

    @Override
    public MaterialDetailVO detail(Long batchId) {
        MatBatchEntity batch = batchMapper.selectOneById(batchId);
        require(batch != null, "批次不存在");
        MaterialDetailVO detail = BeanCopyUtils.copy(toVO(batch), MaterialDetailVO.class);
        detail.setFiles(fileMapper.selectListByQuery(QueryWrapper.create()
                        .where("batch_id = ?", batchId).orderBy("id asc")).stream()
                .map(file -> {
                    MaterialDetailVO.FileItem item = new MaterialDetailVO.FileItem();
                    item.setName(file.getName());
                    item.setExt(file.getExt());
                    item.setSizeBytes(file.getSizeBytes());
                    item.setPageCount(file.getPageCount());
                    item.setStatus(file.getStatus());
                    item.setRejectReason(file.getRejectReason());
                    return item;
                }).toList());
        detail.setChanges(changeLogMapper.selectListByQuery(QueryWrapper.create()
                        .where("batch_id = ?", batchId).orderBy("id desc")).stream()
                .map(change -> {
                    MaterialDetailVO.ChangeItem item = new MaterialDetailVO.ChangeItem();
                    item.setItem(change.getItem());
                    item.setOldValue(change.getOldValue());
                    item.setNewValue(change.getNewValue());
                    item.setOperator(change.getOperator());
                    item.setTime(Times.text(change.getCreateTime()));
                    return item;
                }).toList());
        detail.setLinkedTaskIds(linkedTaskIds(batchId));
        return detail;
    }

    /**
     * 派生态：被任一非草稿任务引用 → 已关联。
     */
    @Override
    public List<Long> linkedTaskIds(Long batchId) {
        return taskMapper.selectListByQuery(QueryWrapper.create()
                        .where("batch_id = ?", batchId).and("status <> ?", "draft")).stream()
                .map(TaskMainEntity::getId).toList();
    }

    private static boolean byPage(String line) {
        return "formula".equals(line) || "layout".equals(line);
    }

    private MaterialVO toVO(MatBatchEntity batch) {
        MaterialVO vo = BeanCopyUtils.copy(batch, MaterialVO.class);
        vo.setLineName(LineRegistry.LINE_NAMES.get(batch.getLine()));
        vo.setCreateTime(Times.text(batch.getCreateTime()));
        vo.setRejectSummary(batch.getRejectSummary() == null || batch.getRejectSummary().isBlank()
                ? List.of() : JsonUtils.parseArray(batch.getRejectSummary(), GROUP_LIST));
        return vo;
    }

    private MaterialRowVO toRowVO(MatBatchEntity batch) {
        MaterialRowVO row = BeanCopyUtils.copy(toVO(batch), MaterialRowVO.class);
        List<Long> linked = linkedTaskIds(batch.getId());
        row.setLinkedTaskCount(linked.size());
        row.setLinked(!linked.isEmpty());
        return row;
    }

    private void logChange(Long batchId, String item, String oldV, String newV) {
        MatChangeLogEntity c = new MatChangeLogEntity();
        c.setBatchId(batchId);
        c.setItem(item);
        c.setOldValue(oldV);
        c.setNewValue(newV);
        c.setOperator(AuthContext.username());
        changeLogMapper.insert(c);
    }

    private static String placeholders(int size) {
        return String.join(", ", java.util.Collections.nCopies(size, "?"));
    }

    private void require(boolean cond, String msg) {
        if (!cond) {
            throw new BizException(msg);
        }
    }

    // ==================== 工具 ====================

    private static String ext(String name) {
        if (name == null) {
            return "";
        }
        int dot = name.lastIndexOf('.');
        return dot < 0 ? "" : name.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    /**
     * 去掉路径分隔，防 zip-slip 与路径注入。
     */
    private static String sanitize(String name) {
        String n = name == null ? "file" : name.replace("\\", "/");
        int slash = n.lastIndexOf('/');
        n = slash >= 0 ? n.substring(slash + 1) : n;
        return n.isBlank() ? "file" : n;
    }

    private static byte[] readAll(MultipartFile f) {
        try (InputStream in = f.getInputStream()) {
            return in.readAllBytes();
        } catch (IOException e) {
            throw new BizException("读取上传文件失败：" + f.getOriginalFilename(), e);
        }
    }

    private static String sha256(byte[] data) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
        } catch (Exception e) {
            throw new BizException("计算文件哈希失败", e);
        }
    }

    /**
     * 编码识别：UTF-8 严格校验 → GB18030（兼容 GBK）；均失败返回 null。
     */
    private static String decodeAuto(byte[] data) {
        if (validUtf8(data)) {
            return new String(data, StandardCharsets.UTF_8);
        }
        try {
            return new String(data, "GB18030");
        } catch (Exception e) {
            log.debug("GB18030 解码失败", e);
            return null;
        }
    }

    private static boolean validUtf8(byte[] data) {
        try {
            CharsetDecoder dec = StandardCharsets.UTF_8.newDecoder();
            dec.decode(ByteBuffer.wrap(data));
            return true;
        } catch (Exception e) {
            log.debug("UTF-8 严格校验失败", e);
            return false;
        }
    }
}
