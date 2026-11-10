/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PORT?: string
  readonly VITE_PUBLIC_PATH?: string
  readonly VITE_API_PROXY_TARGET?: string
  readonly VITE_API_FILE_TARGET?: string
  readonly VITE_QIANKUN_DEV?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
