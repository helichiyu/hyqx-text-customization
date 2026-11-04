package com.wbdz.dto;

/**
 * 素材批次基本信息编辑入参（两项均可选，至少传一项）。
 *
 * @param name 新批次名称
 * @param line 新产线代码
 * @author wbdz
 * @since 2026-11-03
 */
public record MaterialEditDTO(String name, String line) {
}
