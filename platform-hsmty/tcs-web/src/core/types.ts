/**
 * 分页结果契约：消费方只读取 rows 与 total 等冻结字段。
 */
export interface PageResult<T> {
  rows: T[]
  total: number
}
