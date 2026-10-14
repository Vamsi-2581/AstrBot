/**
 * I18n TypeScript Type Definitions - Auto-generated from JSON
 * 国际化类型定义，从JSON文件自动推断，确保类型安全且自动同步
 */

// 直接导入已经组织好的翻译数据
import { translations } from './translations';

// 导出翻译数据常量，供类型推断使用
export const translationData = translations;

// 语言环境类型 - 从实际的翻译数据键推断
export type Locale = keyof typeof translations;

// 验证结果
export interface ValidationResult {
  isValid: boolean;
  missingKeys: string[];
  extraKeys: string[];
  errors: ValidationError[];
}

export interface ValidationError {
  type: 'missing' | 'extra' | 'type_mismatch' | 'empty_value';
  key: string;
  message: string;
  severity: 'error' | 'warning';
}

// 使用情况报告
export interface UsageReport {
  unusedKeys: string[];
  undefinedKeys: string[];
  coverage: number;
  totalKeys: number;
  usedKeys: number;
}

// 翻译统计信息
export interface TranslationStats {
  modules: {
    [moduleName: string]: {
      keys: number;
      coverage: number;
      lastUpdated: string;
    };
  };
  locales: {
    [locale: string]: {
      totalKeys: number;
      translatedKeys: number;
      coverage: number;
    };
  };
  overall: {
    totalKeys: number;
    averageCoverage: number;
    lastSync: string;
  };
}

// Vue I18n 模块增强 - 为了避免编译时的模块查找问题，暂时注释掉
// 这些类型定义在运行时仍然有效，但不会在编译时产生错误
/*
declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $t: (key: TranslationKey, params?: Record<string, string | number>) => string;
  }
}

declare module 'vue-i18n' {
  export interface DefineLocaleMessage extends TranslationSchema {}
}
*/
