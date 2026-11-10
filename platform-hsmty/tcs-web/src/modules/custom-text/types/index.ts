/**
 * 文本定制化生产模块类型定义入口。
 *
 * 业务迁移时在此补充 DTO/VO 映射，内部 Long ID 一律按字符串处理。
 */
export interface CustomTextModuleMeta {
  key: 'custom-text'
  title: string
}
