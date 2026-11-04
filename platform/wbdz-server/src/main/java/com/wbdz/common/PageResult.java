package com.wbdz.common;

import lombok.Data;

import java.util.List;

/**
 * 分页返回结构。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
public class PageResult<T> {

    private long total;
    private long pageNum;
    private long pageSize;
    private List<T> records;

    public static <T> PageResult<T> of(long total, long pageNum, long pageSize, List<T> records) {
        PageResult<T> p = new PageResult<>();
        p.total = total;
        p.pageNum = pageNum;
        p.pageSize = pageSize;
        p.records = records;
        return p;
    }
}
