import eslint from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'

/** 浏览器环境全局变量（Vite 子应用运行在浏览器，不引入 Node globals） */
const browserGlobals = {
  window: 'readonly',
  document: 'readonly',
  navigator: 'readonly',
  location: 'readonly',
  history: 'readonly',
  localStorage: 'readonly',
  sessionStorage: 'readonly',
  URL: 'readonly',
  URLSearchParams: 'readonly',
  Blob: 'readonly',
  File: 'readonly',
  FormData: 'readonly',
  Event: 'readonly',
  HTMLElement: 'readonly',
  HTMLInputElement: 'readonly',
  XMLHttpRequest: 'readonly',
  setTimeout: 'readonly',
  clearTimeout: 'readonly',
}

export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**', 'coverage/**'] },
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },
  {
    files: ['src/**/*.{ts,vue}', 'tests/**/*.ts', '*.config.{js,ts}'],
    languageOptions: {
      globals: browserGlobals,
    },
  },
  {
    // 业务页面承载后端动态 JSON（payload/summary 等结构由算子决定），沿用 any 读取
    files: ['src/modules/**/*.{ts,vue}'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
)
