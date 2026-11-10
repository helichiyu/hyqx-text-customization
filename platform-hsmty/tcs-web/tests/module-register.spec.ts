import { describe, expect, it } from 'vitest'

import { businessModules, collectModuleMenus, collectModuleRoutes } from '@/core/register'

describe('module registry', () => {
  it('registers the custom-text module', () => {
    expect(businessModules.map((module) => module.key)).toContain('custom-text')
  })

  it('collects module routes and menus', () => {
    expect(collectModuleRoutes().some((route) => route.path === '/custom-text')).toBe(true)
    expect(collectModuleMenus().some((menu) => menu.component === 'custom-text/Home')).toBe(true)
  })
})
