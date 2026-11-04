package com.wbdz.common;

import lombok.Data;

/**
 * 分页查询基类（pageNum 从 1 开始）。
 *
 * @author wbdz
 * @since 2026-11-03
 */
@Data
public class PageQuery {

    private Integer pageNum = 1;
    private Integer pageSize = 10;

    public long offset() {
        return (long) (Math.max(1, pageNum) - 1) * Math.max(1, pageSize);
    }

    public int limit() {
        return Math.min(200, Math.max(1, pageSize));
    }
}
