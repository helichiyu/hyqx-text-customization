package com.wbdz;

import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import com.wbdz.entity.Dataset;
import com.wbdz.entity.DatasetItem;
import com.wbdz.entity.DeliveryLog;
import com.wbdz.entity.MatBatch;
import com.wbdz.entity.MatChangeLog;
import com.wbdz.entity.MatFile;
import com.wbdz.entity.ParamDraft;
import com.wbdz.entity.ParamVersion;
import com.wbdz.entity.ReviewItem;
import com.wbdz.entity.ReviewOrder;
import com.wbdz.entity.RollbackLog;
import com.wbdz.entity.SysUser;
import com.wbdz.entity.TaskMain;
import com.wbdz.entity.TaskStageRun;
import org.junit.jupiter.api.Test;

import java.io.Serializable;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 持久化实体规范契约测试。
 *
 * @author wbdz
 * @since 2026-11-05
 */
class PersistenceContractTest {

    private static final List<Class<?>> ENTITIES = List.of(
            Dataset.class, DatasetItem.class, DeliveryLog.class, MatBatch.class, MatChangeLog.class,
            MatFile.class, ParamDraft.class, ParamVersion.class, ReviewItem.class, ReviewOrder.class,
            RollbackLog.class, SysUser.class, TaskMain.class, TaskStageRun.class);

    @Test
    void allEntitiesAreSerializableAndMapped() throws Exception {
        for (Class<?> entity : ENTITIES) {
            assertThat(Serializable.class).isAssignableFrom(entity);
            assertThat(entity.getDeclaredField("serialVersionUID")).isNotNull();
            assertThat(entity.getAnnotation(Table.class)).isNotNull();
        }
    }

    @Test
    void logicDeleteColumnsRemainConfigured() throws Exception {
        assertThat(TaskMain.class.getDeclaredField("delFlag").getAnnotation(Column.class).isLogicDelete()).isTrue();
        assertThat(MatBatch.class.getDeclaredField("delFlag").getAnnotation(Column.class).isLogicDelete()).isTrue();
    }
}