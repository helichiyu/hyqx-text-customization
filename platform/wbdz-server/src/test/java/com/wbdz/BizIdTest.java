package com.wbdz;

import com.wbdz.common.BizId;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 业务编号生成器：格式 / 字符集（无 0 O 1 I L）/ 唯一性。
 *
 * @author wbdz
 * @since 2026-11-03
 */
class BizIdTest {

    private static final String SAFE = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";

    @Test
    void formatIsPrefixPlusDatePlusSixRandom() {
        String id = BizId.next("TASK");
        String today = LocalDate.now().format(DateTimeFormatter.ofPattern("yyMMdd"));
        assertThat(id).startsWith("TASK" + today).hasSize("TASK".length() + 6 + 6);
    }

    @Test
    void randomPartUsesSafeCharsetOnly() {
        for (int i = 0; i < 500; i++) {
            String tail = BizId.next("DS").substring(8);
            for (char c : tail.toCharArray()) {
                assertThat(SAFE.indexOf(c)).as("字符 %s 不在安全字符集", c).isGreaterThanOrEqualTo(0);
            }
        }
    }

    @Test
    void tenThousandIdsAreUnique() {
        Set<String> seen = new HashSet<>();
        for (int i = 0; i < 10_000; i++) {
            seen.add(BizId.next("CR"));
        }
        assertThat(seen).hasSize(10_000);
    }
}
