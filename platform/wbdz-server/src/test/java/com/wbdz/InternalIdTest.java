package com.wbdz;

import com.mybatisflex.core.keygen.impl.FlexIDKeyGenerator;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 内部主键生成器契约：正 Long、当前 18 位、趋势唯一。
 *
 * <p>结论：内部主键不对外暴露，当前 flexId 为 18 位且离 19 位边界仍有充足空间，
 * 本轮不强制造 19 位，继续以 Long 全局唯一性为准。
 *
 * @author wbdz
 * @since 2026-11-05
 */
class InternalIdTest {

    @Test
    void flexIdIsPositiveAndCurrentlyEighteenDigits() {
        FlexIDKeyGenerator generator = new FlexIDKeyGenerator();
        Set<Long> ids = new HashSet<>();
        for (int i = 0; i < 1_000; i++) {
            Long id = (Long) generator.generate(null, null);
            assertThat(id).isPositive();
            assertThat(String.valueOf(id)).hasSize(18);
            ids.add(id);
        }
        assertThat(ids).hasSize(1_000);
    }
}