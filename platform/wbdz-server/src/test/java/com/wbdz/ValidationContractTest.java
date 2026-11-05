package com.wbdz;

import com.wbdz.dto.MaterialEditDTO;
import com.wbdz.dto.ReviewConcludeDTO;
import com.wbdz.dto.TaskThresholdDTO;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * DTO Bean Validation 契约测试。
 *
 * @author wbdz
 * @since 2026-11-05
 */
class ValidationContractTest {

    private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

    @Test
    void materialEditRequiresAtLeastOneField() {
        assertThat(validator.validate(new MaterialEditDTO(null, " ")))
                .extracting(v -> v.getMessage())
                .contains("批次名称和产线至少修改一项");
    }

    @Test
    void thresholdRejectsOutOfRangeValues() {
        assertThat(validator.validate(new TaskThresholdDTO(new BigDecimal("1.1"))))
                .extracting(v -> v.getMessage())
                .contains("阈值不能大于 1");
        assertThat(validator.validate(new TaskThresholdDTO(BigDecimal.ZERO)))
                .extracting(v -> v.getMessage())
                .contains("阈值必须大于 0");
    }

    @Test
    void reviewConclusionOnlyAcceptsAbc() {
        assertThat(validator.validate(new ReviewConcludeDTO("D", null)))
                .extracting(v -> v.getMessage())
                .contains("结论只能是 A、B 或 C");
    }
}