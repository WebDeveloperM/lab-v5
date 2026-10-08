import Breadcrumb from '../../components/Breadcrumbs/Breadcrumb';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import axioss from '../../api/axios';
import { normalizeRole } from '../../utils/pageAccess';

/**
 * Laboratoriya pasport ilovasining bo'limlari va huquqlari.
 *
 * СИЗ (PPE) quyi tizimi loyihadan butunlay olib tashlangan, shuning uchun bu yerda
 * ham, server javobida ham faqat quyidagi kalitlar bor. PATCH da row.pages /
 * row.features butunlay yuboriladi — backend esa faqat kelgan kalitlarni yangilaydi.
 */

type AccessFlags = Record<string, boolean>;

type AccessRow = {
  role: string;
  role_label: string;
  pages: AccessFlags;
  features: AccessFlags;
  is_locked: boolean;
};

type ColumnDef = { key: string; label: string; hint: string };

const PAGE_COLUMNS: ColumnDef[] = [
  { key: 'dashboard', label: 'Главная', hint: 'Сводка по паспортам и справкам' },
  { key: 'passports', label: 'Паспорта', hint: 'Раздел «Паспорта» в меню' },
  { key: 'pending_approvals', label: 'На подписи мне', hint: 'Документы, ожидающие подписи этого сотрудника' },
  { key: 'spravki', label: 'Справки', hint: 'Раздел «Справки» в меню' },
  { key: 'settings', label: 'Настройки', hint: 'Раздел «Настройки» в меню' },
];

const FEATURE_COLUMNS: ColumnDef[] = [
  { key: 'passport_create', label: 'Создание паспорта', hint: 'Кнопка «Добавить» и POST /passports/' },
  { key: 'passport_edit', label: 'Редактирование', hint: 'Изменение паспорта до отправки на подпись' },
  { key: 'passport_delete', label: 'Удаление паспорта', hint: 'Мягкое удаление паспорта' },
  { key: 'spravka_create', label: 'Создание справки', hint: 'Кнопка «Добавить справку» и POST /spravki/' },
];

const getBackendError = (error: any, fallback: string) => {
  const data = error?.response?.data;
  if (!data) return fallback;
  if (typeof data?.error === 'string' && data.error.trim()) return data.error;
  if (typeof data?.detail === 'string' && data.detail.trim()) return data.detail;
  const firstField = Object.values(data)[0];
  if (Array.isArray(firstField) && firstField.length) {
    return String(firstField[0]);
  }
  return fallback;
};

const rowSignature = (row: AccessRow) => {
  const pick = (flags: AccessFlags, columns: ColumnDef[]) =>
    columns.map((column) => (flags?.[column.key] ? '1' : '0')).join('');
  return `${pick(row.pages, PAGE_COLUMNS)}|${pick(row.features, FEATURE_COLUMNS)}`;
};

const thBase =
  'whitespace-nowrap px-3 py-2 text-center text-xs font-semibold text-black dark:text-white';
const cellBase = 'px-3 py-3 text-center';

const PageAccessPage = () => {
  const navigate = useNavigate();
  const role = useMemo(() => normalizeRole(localStorage.getItem('role')), []);
  const isAdmin = role === 'admin';

  const [loading, setLoading] = useState(true);
  const [savingRole, setSavingRole] = useState<string | null>(null);
  const [rows, setRows] = useState<AccessRow[]>([]);
  // Serverdagi holat: qaysi qatorlar o'zgarganini shu bilan solishtiramiz.
  const [baseline, setBaseline] = useState<Record<string, string>>({});
  const [customRoleKeys, setCustomRoleKeys] = useState<Set<string>>(new Set());

  const loadPageAccess = async () => {
    setLoading(true);
    try {
      const [accessResponse, rolesResponse] = await Promise.all([
        axioss.get('/users/page-access-settings/'),
        // Custom rollarni belgilash uchun; ro'yxat kelmasa sahifa baribir ishlayveradi.
        axioss.get('/users/settings-roles/').catch(() => ({ data: [] })),
      ]);

      const nextRows: AccessRow[] = Array.isArray(accessResponse.data) ? accessResponse.data : [];
      setRows(nextRows);
      setBaseline(Object.fromEntries(nextRows.map((row) => [row.role, rowSignature(row)])));

      const rolesData = Array.isArray(rolesResponse.data) ? rolesResponse.data : [];
      setCustomRoleKeys(new Set(rolesData.filter((item: any) => item?.is_custom).map((item: any) => item.key)));
    } catch (error) {
      toast.error(getBackendError(error, 'Не удалось загрузить доступы к страницам'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isAdmin) {
      setLoading(false);
      return;
    }
    loadPageAccess();
  }, [isAdmin]);

  const toggle = (roleKey: string, group: 'pages' | 'features', flagKey: string, value: boolean) => {
    setRows((prev) => prev.map((row) => (
      row.role === roleKey
        ? { ...row, [group]: { ...row[group], [flagKey]: value } }
        : row
    )));
  };

  const isDirty = (row: AccessRow) => !row.is_locked && baseline[row.role] !== rowSignature(row);
  const dirtyRows = rows.filter(isDirty);

  const saveRow = async (row: AccessRow) => {
    if (row.is_locked) return true;

    setSavingRole(row.role);
    try {
      const response = await axioss.patch('/users/page-access-settings/', {
        role: row.role,
        pages: row.pages,
        features: row.features,
      });
      const saved: AccessRow = response.data;
      setRows((prev) => prev.map((entry) => (entry.role === row.role ? saved : entry)));
      setBaseline((prev) => ({ ...prev, [row.role]: rowSignature(saved) }));
      return true;
    } catch (error) {
      toast.error(getBackendError(error, `Не удалось сохранить роль «${row.role_label}»`));
      return false;
    } finally {
      setSavingRole(null);
    }
  };

  const handleSaveRow = async (row: AccessRow) => {
    if (await saveRow(row)) {
      toast.success(`Доступы для роли «${row.role_label}» сохранены`);
    }
  };

  const handleSaveAll = async () => {
    const pending = [...dirtyRows];
    let saved = 0;
    for (const row of pending) {
      // Ketma-ket: xato bo'lsa qaysi rolda to'xtaganini aniq ko'rsatadi.
      if (!(await saveRow(row))) break;
      saved += 1;
    }
    if (saved) {
      toast.success(`Сохранено ролей: ${saved}`);
    }
  };

  if (!isAdmin) {
    return (
      <>
        <Breadcrumb pageName="Доступ к страницам" />
        <div className="rounded-sm border border-stroke bg-white p-5 shadow-default dark:border-strokedark dark:bg-boxdark">
          <p className="text-sm text-black dark:text-white">Эта страница доступна только администратору.</p>
        </div>
      </>
    );
  }

  const renderCheckbox = (row: AccessRow, group: 'pages' | 'features', column: ColumnDef) => {
    const checked = Boolean(row[group]?.[column.key]);
    return (
      <td key={column.key} className={cellBase}>
        <input
          type="checkbox"
          checked={row.is_locked ? true : checked}
          disabled={row.is_locked || savingRole === row.role}
          onChange={(event) => toggle(row.role, group, column.key, event.target.checked)}
          aria-label={`${row.role_label} — ${column.label}`}
          className="h-4 w-4 cursor-pointer accent-primary disabled:cursor-not-allowed disabled:opacity-60"
        />
      </td>
    );
  };

  return (
    <>
      <Breadcrumb pageName="Доступ к страницам" />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => navigate('/nastroyka')}
          className="rounded border border-stroke bg-white px-4 py-2 text-sm font-medium text-black hover:bg-gray-50 dark:border-strokedark dark:bg-boxdark dark:text-white dark:hover:bg-meta-4"
        >
          ← Назад
        </button>
        <button
          type="button"
          onClick={loadPageAccess}
          disabled={loading || savingRole !== null}
          className="rounded border border-stroke bg-white px-4 py-2 text-sm font-medium text-black hover:bg-gray-50 disabled:opacity-60 dark:border-strokedark dark:bg-boxdark dark:text-white dark:hover:bg-meta-4"
        >
          Обновить
        </button>
        {dirtyRows.length > 0 && (
          <button
            type="button"
            onClick={handleSaveAll}
            disabled={savingRole !== null}
            className="rounded bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            Сохранить всё ({dirtyRows.length})
          </button>
        )}
      </div>

      <div className="rounded-sm border border-stroke bg-white shadow-default dark:border-strokedark dark:bg-boxdark">
        <div className="border-b border-stroke px-6 py-4 dark:border-strokedark">
          <h3 className="text-base font-semibold text-black dark:text-white">Управление доступом по ролям</h3>
          <p className="mt-1 text-sm text-bodydark2">
            «Разделы меню» — что роль видит в боковом меню. «Права» — что она может делать с паспортами
            и справками. Те же значения проверяет и сервер, поэтому снятая галочка закрывает действие,
            а не только прячет кнопку.
          </p>
        </div>

        {loading ? (
          <div className="py-16 text-center text-sm text-bodydark2">Загрузка...</div>
        ) : rows.length === 0 ? (
          <div className="py-16 text-center text-sm text-bodydark2">Роли не найдены</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] border-collapse">
              <thead>
                <tr className="bg-gray-2 dark:bg-meta-4">
                  <th rowSpan={2} className={`${thBase} sticky left-0 z-10 bg-gray-2 text-left dark:bg-meta-4`}>
                    Роль
                  </th>
                  <th colSpan={PAGE_COLUMNS.length} className={`${thBase} border-l border-stroke dark:border-strokedark`}>
                    Разделы меню
                  </th>
                  <th colSpan={FEATURE_COLUMNS.length} className={`${thBase} border-l border-stroke dark:border-strokedark`}>
                    Права
                  </th>
                  <th rowSpan={2} className={`${thBase} border-l border-stroke dark:border-strokedark`}>
                    Действие
                  </th>
                </tr>
                <tr className="bg-gray-2 dark:bg-meta-4">
                  {PAGE_COLUMNS.map((column, index) => (
                    <th
                      key={column.key}
                      title={column.hint}
                      className={`${thBase} font-medium ${index === 0 ? 'border-l border-stroke dark:border-strokedark' : ''}`}
                    >
                      {column.label}
                    </th>
                  ))}
                  {FEATURE_COLUMNS.map((column, index) => (
                    <th
                      key={column.key}
                      title={column.hint}
                      className={`${thBase} font-medium ${index === 0 ? 'border-l border-stroke dark:border-strokedark' : ''}`}
                    >
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const dirty = isDirty(row);
                  return (
                    <tr
                      key={row.role}
                      className={`border-t border-stroke dark:border-strokedark ${dirty ? 'bg-amber-50 dark:bg-amber-950/20' : ''}`}
                    >
                      <td
                        className={`sticky left-0 z-10 px-4 py-3 text-left ${dirty ? 'bg-amber-50 dark:bg-amber-950/20' : 'bg-white dark:bg-boxdark'}`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-black dark:text-white">{row.role_label}</span>
                          {customRoleKeys.has(row.role) && (
                            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                              своя
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-bodydark2">{row.role}</div>
                      </td>

                      {PAGE_COLUMNS.map((column) => renderCheckbox(row, 'pages', column))}
                      {FEATURE_COLUMNS.map((column) => renderCheckbox(row, 'features', column))}

                      <td className="px-3 py-3 text-center">
                        {row.is_locked ? (
                          <span className="text-xs text-bodydark2">Всегда включено</span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleSaveRow(row)}
                            disabled={!dirty || savingRole !== null}
                            className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {savingRole === row.role ? '...' : 'Сохранить'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="border-t border-stroke px-6 py-3 text-xs text-bodydark2 dark:border-strokedark">
          Роль «Админ» всегда имеет полный доступ и не редактируется. Новые роли создаются на странице
          «Пользователи» и появляются здесь с минимальными правами.
        </div>
      </div>
    </>
  );
};

export default PageAccessPage;
