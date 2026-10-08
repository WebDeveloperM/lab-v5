import Breadcrumb from '../../components/Breadcrumbs/Breadcrumb';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import axioss from '../../api/axios';
import { getStoredPageAccess } from '../../utils/pageAccess';

type Department = {
  id: number;
  name: string;
  boss_fullName: string;
};

type Section = {
  id: number;
  department: number;
  department_name: string;
  name: string;
};

type ResponsiblePerson = {
  id: number;
  full_name: string;
  position: string;
};

type SettingsUser = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'it_center' | 'shift_head' | 'sttl_head' | 'czl_head' | 'dispatcher' | 'user';
  base_avatar?: string | null;
  is_superuser?: boolean;
  is_active?: boolean;
};

type Employee = {
  id: number;
  slug: string;
  first_name: string;
  last_name: string;
  surname: string;
  tabel_number: string;
  position: string;
  requires_face_id_checkout: boolean;
};

const normalizeRole = (rawRole: string | null): 'admin' | 'it_center' | 'shift_head' | 'sttl_head' | 'czl_head' | 'dispatcher' | 'user' => {
  const value = String(rawRole || '').trim().toLowerCase();
  if (value === 'admin' || value === 'админ') return 'admin';
  if (value === 'it_center' || value === 'it-center' || value === 'it center') return 'it_center';
  if (value === 'shift_head' || value === 'начальник смены') return 'shift_head';
  if (value === 'sttl_head' || value === 'начальник сттл') return 'sttl_head';
  if (value === 'czl_head' || value === 'начальник цзл') return 'czl_head';
  if (value === 'dispatcher' || value === 'диспетчер') return 'dispatcher';
  return 'user';
};

const isManagerTierRole = (role: string) => role === 'shift_head' || role === 'sttl_head' || role === 'czl_head' || role === 'dispatcher';

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

// Icon components
const FactoryIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/>
    <path d="M17 18h1"/><path d="M12 18h1"/><path d="M7 18h1"/>
  </svg>
);

const BuildingIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 22V10a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v12"/>
    <path d="M6 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2"/>
    <path d="M18 22h2a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-2"/>
    <path d="M10 22v-4h4v4"/>
    <path d="M10 10h4"/><path d="M12 10v12"/>
  </svg>
);

const UserCheckIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <polyline points="16 11 18 13 22 9"/>
  </svg>
);

const UsersIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const LockIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="10" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const TemplateIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6" />
    <path d="M8 12h8" /><path d="M8 16h5" />
    <path d="M10 8H8" />
  </svg>
);

const NastroykaPage = () => {
  const navigate = useNavigate();
  const role = useMemo(() => normalizeRole(localStorage.getItem('role')), []);
  const pageAccess = useMemo(() => getStoredPageAccess(role), [role]);
  const canManageSettings = pageAccess.settings;
  const isAdmin = role === 'admin';
  const canEditBaseSettings = role === 'admin' || role === 'it_center' || isManagerTierRole(role);

  const [loading, setLoading] = useState(true);

  const [departments, setDepartments] = useState<Department[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [persons, setPersons] = useState<ResponsiblePerson[]>([]);
  const [users, setUsers] = useState<SettingsUser[]>([]);
  const [usersCount, setUsersCount] = useState(0);
  const [templatesCount, setTemplatesCount] = useState(0);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const [departmentsRes, sectionsRes, personsRes, templatesRes] = await Promise.all([
        axioss.get('/settings/departments/'),
        axioss.get('/settings/sections/'),
        axioss.get('/settings/responsible-persons/'),
        axioss.get('/passport-templates/'),
      ]);

      setDepartments(departmentsRes.data || []);
      setSections(sectionsRes.data || []);
      setPersons(personsRes.data || []);
      setTemplatesCount(Array.isArray(templatesRes.data) ? templatesRes.data.length : templatesRes.data?.count ?? 0);

      if (role === 'admin') {
        const usersRes = await axioss.get('/users/settings-users/');
        const usersPayload = usersRes.data || {};
        const results = Array.isArray(usersPayload) ? usersPayload : usersPayload.results || [];
        setUsers(results);
        setUsersCount(Array.isArray(usersPayload) ? results.length : Number(usersPayload.count || 0));
      } else {
        setUsers([]);
        setUsersCount(0);
      }
    } catch (error) {
      toast.error(getBackendError(error, 'Не удалось загрузить данные настроек'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!canManageSettings) {
      setLoading(false);
      return;
    }
    if (isAdmin || role === 'it_center' || isManagerTierRole(role)) {
      loadSettings();
    } else {
      setLoading(false);
    }
  }, [canManageSettings, isAdmin, role]);


  // Card component for main menu
  const SettingCard = ({ icon: Icon, title, count, onClick, color }: { icon: any; title: string; count: number; onClick: () => void; color: string }) => (
    <button
      onClick={onClick}
      className="flex flex-col items-center justify-center rounded-lg border border-stroke bg-white p-6 shadow-default transition-all hover:shadow-lg dark:border-strokedark dark:bg-boxdark"
    >
      <div className={`mb-4 rounded-full p-4 ${color}`}>
        <Icon />
      </div>
      <h3 className="mb-2 text-base font-semibold text-black dark:text-white">{title}</h3>
      <span className="text-sm text-gray-500 dark:text-gray-400">Всего: {count}</span>
    </button>
  );

  return (
    <>
      <Breadcrumb pageName="Настройки" />

      {!canManageSettings ? (
        <div className="rounded-sm border border-stroke bg-white p-5 shadow-default dark:border-strokedark dark:bg-boxdark">
          <div className="text-base text-red-600">Нет доступа к странице</div>
          <div className="mt-2 text-sm text-slate-700 dark:text-slate-300">
            Только admin, it_center, shift_head, sttl_head, czl_head или dispatcher могут использовать этот раздел.
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {loading && (
            <div className="rounded-sm border border-stroke bg-white p-4 text-sm dark:border-strokedark dark:bg-boxdark">
              Загрузка...
            </div>
          )}

          {/* Main Menu Cards */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {canEditBaseSettings && (
              <>
                <SettingCard
                  icon={FactoryIcon}
                  title="Цех"
                  count={departments.length}
                  onClick={() => navigate('/nastroyka/department')}
                  color="bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                />
                <SettingCard
                  icon={BuildingIcon}
                  title="Отдел"
                  count={sections.length}
                  onClick={() => navigate('/nastroyka/section')}
                  color="bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400"
                />
                <SettingCard
                  icon={UserCheckIcon}
                  title="Ответственное лицо"
                  count={persons.length}
                  onClick={() => navigate('/nastroyka/person')}
                  color="bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400"
                />
              </>
            )}
            {isAdmin && (
              <>
                <SettingCard
                  icon={UsersIcon}
                  title="Пользователи"
                  count={usersCount}
                  onClick={() => navigate('/nastroyka/user')}
                  color="bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                />
                <SettingCard
                  icon={LockIcon}
                  title="Доступ к страницам"
                  count={4}
                  onClick={() => navigate('/nastroyka/page-access')}
                  color="bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
                />
              </>
            )}
            {canEditBaseSettings && (
              <SettingCard
                icon={TemplateIcon}
                title="Шаблоны паспортов"
                count={templatesCount}
                onClick={() => navigate('/nastroyka/passport-templates')}
                color="bg-rose-100 text-rose-600 dark:bg-rose-900/30 dark:text-rose-400"
              />
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default NastroykaPage;
