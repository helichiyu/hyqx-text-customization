package com.wbdz;

import com.wbdz.service.ParamService;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 参数版本号自增规则。
 *
 * @author wbdz
 * @since 2026-11-03
 */
class ParamServiceTest {

    @Test
    void bumpIncrementsMinor() {
        assertThat(ParamService.bump("v1.0")).isEqualTo("v1.1");
        assertThat(ParamService.bump("v1.9")).isEqualTo("v1.10");
        assertThat(ParamService.bump("v2.3")).isEqualTo("v2.4");
    }

    @Test
    void bumpFirstVersionAndBadInput() {
        assertThat(ParamService.bump(null)).isEqualTo("v1.0");
        assertThat(ParamService.bump("")).isEqualTo("v1.0");
        assertThat(ParamService.bump("draft")).isEqualTo("v1.0");
    }
}
