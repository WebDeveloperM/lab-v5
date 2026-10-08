export type NormalizedRole = 'admin' | 'it_center' | 'shift_head' | 'sttl_head' | 'czl_head' | 'dispatcher' | 'user';

// These four roles share most page/feature defaults below — they replace the single
// consolidated laboratory_manager role with per-position labels.
export const MANAGER_TIER_ROLES: NormalizedRole[] = ['shift_head', 'sttl_head', 'czl_head', 'dispatcher'];
export const isManagerTierRole = (role: NormalizedRole) => (MANAGER_TIER_ROLES as string[]).includes(role);

// Laboratoriya pasport ilovasining bo'limlari. СИЗ (PPE) quyi tizimi loyihadan
// butunlay olib tashlandi, shuning uchun bu yerda ppe_arrival/statistics kalitlari yo'q.
export type PageAccess = {
  dashboard: boolean;
  passports: boolean;
  pending_approvals: boolean;
  spravki: boolean;
  settings: boolean;
};

// Pasport oqimining huquqlari. Ilgari ular komponentlarda rol nomiga qattiq bog'langan edi.
export type FeatureAccess = {
  passport_create: boolean;
  passport_edit: boolean;
  passport_delete: boolean;
  spravka_create: boolean;
};

const PAGE_ACCESS_STORAGE_KEY = 'page_access';
const FEATURE_ACCESS_STORAGE_KEY = 'feature_access';

// «На подписи мне» ilgari Sidebar-da qattiq yozilgan edi: admin + СТТЛ/ЦЗЛ/Диспетчер.
const PENDING_APPROVAL_DEFAULT_ROLES: NormalizedRole[] = ['sttl_head', 'czl_head', 'dispatcher'];

export const normalizeRole = (rawRole: string | null): NormalizedRole => {
  const value = String(rawRole || '').trim().toLowerCase();
  if (value === 'admin' || value === 'админ') return 'admin';
  if (value === 'it_center' || value === 'it-center' || value === 'it center') return 'it_center';
  if (value === 'shift_head' || value === 'начальник смены') return 'shift_head';
  if (value === 'sttl_head' || value === 'начальник сттл') return 'sttl_head';
  if (value === 'czl_head' || value === 'начальник цзл') return 'czl_head';
  if (value === 'dispatcher' || value === 'диспетчер') return 'dispatcher';
  // Админ qo'shgan custom rollar shu yerga tushadi: ular rol nomiga bog'langan hech qanday
  // imtiyoz olmaydi — huquqlari faqat serverdan kelgan page_access/feature_access bilan belgilanadi.
  return 'user';
};

export const getDefaultPageAccess = (role: NormalizedRole): PageAccess => {
  // passports va spravki hamma joyda true: bu ikki bo'lim ilgari har qanday
  // autentifikatsiyalangan rolga ochiq edi, false qilish ularni jimgina yopib qo'yardi.
  const minimal: PageAccess = {
    dashboard: true,
    passports: true,
    pending_approvals: false,
    spravki: true,
    settings: false,
  };

  const privileged = role === 'admin' || role === 'it_center' || isManagerTierRole(role);
  if (!privileged) {
    return minimal;
  }

  return {
    dashboard: true,
    passports: true,
    pending_approvals: role === 'admin' || PENDING_APPROVAL_DEFAULT_ROLES.includes(role),
    spravki: true,
    settings: true,
  };
};

export const getDefaultFeatureAccess = (role: NormalizedRole): FeatureAccess => {
  // Паспортni tahrirlash ilgari "role !== user" sharti edi.
  const minimal: FeatureAccess = {
    passport_create: false,
    passport_edit: false,
    passport_delete: false,
    spravka_create: false,
  };

  if (role === 'admin') {
    return {
      passport_create: true,
      passport_edit: true,
      passport_delete: true,
      spravka_create: true,
    };
  }

  if (role === 'it_center') {
    return { ...minimal, passport_edit: true };
  }

  if (isManagerTierRole(role)) {
    const isShiftHead = role === 'shift_head';
    return {
      passport_create: isShiftHead,
      passport_edit: true,
      passport_delete: false,
      spravka_create: isShiftHead,
    };
  }

  return minimal;
};

/**
 * Serverdan kelgan qiymatni standart bilan birlashtiradi: faqat haqiqiy boolean bo'lgan
 * kalitlar olinadi, qolgani standartda qoladi. Shu tufayli backend yangi kalit qo'shganda
 * eski frontend sinmaydi va aksincha.
 */
const mergeAccess = <T extends Record<string, boolean>>(raw: any, defaults: T): T => {
  if (!raw || typeof raw !== 'object') {
    return defaults;
  }

  const merged = { ...defaults };
  (Object.keys(defaults) as Array<keyof T>).forEach((key) => {
    const value = raw[key as string];
    if (typeof value === 'boolean') {
      merged[key] = value as T[keyof T];
    }
  });
  return merged;
};

export const normalizePageAccess = (rawPageAccess: any, role: NormalizedRole): PageAccess =>
  mergeAccess(rawPageAccess, getDefaultPageAccess(role));

export const normalizeFeatureAccess = (rawFeatureAccess: any, role: NormalizedRole): FeatureAccess =>
  mergeAccess(rawFeatureAccess, getDefaultFeatureAccess(role));

const readStored = <T extends Record<string, boolean>>(storageKey: string, defaults: T): T => {
  let rawValue: string | null = null;
  try {
    rawValue = localStorage.getItem(storageKey);
  } catch {
    return defaults;
  }

  if (!rawValue) {
    return defaults;
  }

  try {
    return mergeAccess(JSON.parse(rawValue), defaults);
  } catch {
    return defaults;
  }
};

export const getStoredPageAccess = (role?: NormalizedRole): PageAccess =>
  readStored(PAGE_ACCESS_STORAGE_KEY, getDefaultPageAccess(role || normalizeRole(localStorage.getItem('role'))));

export const storePageAccess = (pageAccess: PageAccess) => {
  localStorage.setItem(PAGE_ACCESS_STORAGE_KEY, JSON.stringify(pageAccess));
};

export const getStoredFeatureAccess = (role?: NormalizedRole): FeatureAccess =>
  readStored(FEATURE_ACCESS_STORAGE_KEY, getDefaultFeatureAccess(role || normalizeRole(localStorage.getItem('role'))));

export const storeFeatureAccess = (featureAccess: FeatureAccess) => {
  localStorage.setItem(FEATURE_ACCESS_STORAGE_KEY, JSON.stringify(featureAccess));
};

export const clearStoredPageAccess = () => {
  localStorage.removeItem(PAGE_ACCESS_STORAGE_KEY);
  localStorage.removeItem(FEATURE_ACCESS_STORAGE_KEY);
};

// Sidebar tartibiga mos: foydalanuvchi kira oladigan birinchi bo'lim.
export const getFirstAccessibleRoute = (pageAccess: PageAccess) => {
  if (pageAccess.dashboard) return '/';
  if (pageAccess.passports) return '/pasporta';
  if (pageAccess.pending_approvals) return '/pasporta/pending-approvals';
  if (pageAccess.spravki) return '/spravki';
  if (pageAccess.settings) return '/nastroyka';
  return null;
};
