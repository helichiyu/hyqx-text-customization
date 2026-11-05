package com.wbdz;

import com.wbdz.entity.TaskMain;
import com.wbdz.mapper.TaskMainMapper;
import com.wbdz.service.DataSeeder;
import com.wbdz.service.TaskService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.jdbc.Sql;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 逻辑删除隔离集成测试。
 *
 * @author wbdz
 * @since 2026-11-05
 */
@SpringBootTest(properties = {
        "spring.datasource.url=jdbc:h2:mem:wbdz_logic_delete;MODE=MySQL;DB_CLOSE_DELAY=-1;NON_KEYWORDS=LINE",
        "spring.datasource.driver-class-name=org.h2.Driver",
        "spring.datasource.username=sa",
        "spring.datasource.password=",
        "spring.liquibase.enabled=false",
        "spring.sql.init.mode=never",
        "wbdz.storage-dir=./target/test-storage",
        "wbdz.op-runtime-dir=./target/test-op-runtime"
})
class LogicDeleteIntegrationTest {

    @Autowired
    private TaskMainMapper taskMapper;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @MockitoBean
    private DataSeeder dataSeeder;

    @BeforeEach
    void createSchema() {
        jdbcTemplate.execute("DROP TABLE IF EXISTS wbdz_task");
        jdbcTemplate.execute("""
                CREATE TABLE wbdz_task (
                    id BIGINT PRIMARY KEY,
                    biz_no VARCHAR(32),
                    name VARCHAR(100),
                    line VARCHAR(32),
                    status VARCHAR(32),
                    priority VARCHAR(16),
                    image_class VARCHAR(32),
                    batch_id BIGINT,
                    param_version VARCHAR(32),
                    param_snapshot CLOB,
                    threshold DECIMAL(6, 4),
                    current_stage INT,
                    create_by VARCHAR(64),
                    create_time TIMESTAMP,
                    update_time TIMESTAMP,
                    del_flag VARCHAR(1) DEFAULT 'F'
                )
                """);
    }

    @Test
    void deletedRowIsHiddenFromMapperButRetainedInDatabase() {
        TaskMain task = new TaskMain();
        task.setBizNo("TASK261105ABCDEF");
        task.setName("逻辑删除测试");
        task.setLine("metadata");
        task.setStatus("draft");
        task.setPriority("mid");
        task.setThreshold(new BigDecimal("0.80"));
        task.setCurrentStage(0);
        taskMapper.insert(task);

        assertThat(task.getId()).isNotNull();
        assertThat(taskMapper.selectOneById(task.getId())).isNotNull();

        taskMapper.deleteById(task.getId());

        assertThat(taskMapper.selectOneById(task.getId())).isNull();
        Integer retained = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM wbdz_task WHERE id = ? AND del_flag = 'T'",
                Integer.class, task.getId());
        assertThat(retained).isEqualTo(1);
    }
}