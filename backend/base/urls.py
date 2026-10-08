from django.urls import path

from base.views import (
    SettingsDepartmentDetailApiView,
    SettingsDepartmentListCreateApiView,
    SettingsResponsiblePersonDetailApiView,
    SettingsResponsiblePersonListCreateApiView,
    SettingsSectionDetailApiView,
    SettingsSectionListCreateApiView,
)
from base.employee_service_views import (
    EmployeeServiceBaseImageChangeLogDetailApiView,
    EmployeeServiceBaseImageChangeLogListApiView,
    EmployeeServiceDepartmentDetailApiView,
    EmployeeServiceDepartmentListApiView,
    EmployeeServiceEmployeeDetailApiView,
    EmployeeServiceEmployeeListApiView,
    EmployeeServiceMediaProxyApiView,
    EmployeeServiceSectionDetailApiView,
    EmployeeServiceSectionListApiView,
)

# СИЗ (PPE) quyi tizimi loyihadan olib tashlandi — u bilan birga item/pending-issue/
# issue-qr/statistics/ppe-* va face-id-exemption marshrutlari ham yo'q qilindi.
# Bu yerda faqat pasport oqimiga kerak bo'lgan ma'lumotnomalar qoldi.
urlpatterns = [
    path("settings/departments/", SettingsDepartmentListCreateApiView.as_view()),
    path("settings/departments/<int:pk>/", SettingsDepartmentDetailApiView.as_view()),
    path("settings/sections/", SettingsSectionListCreateApiView.as_view()),
    path("settings/sections/<int:pk>/", SettingsSectionDetailApiView.as_view()),
    path("settings/responsible-persons/", SettingsResponsiblePersonListCreateApiView.as_view()),
    path("settings/responsible-persons/<int:pk>/", SettingsResponsiblePersonDetailApiView.as_view()),

    # Employee Service proksi qatlami
    path("employee-service/departments/", EmployeeServiceDepartmentListApiView.as_view()),
    path("employee-service/departments/<int:department_id>/", EmployeeServiceDepartmentDetailApiView.as_view()),
    path("employee-service/sections/", EmployeeServiceSectionListApiView.as_view()),
    path("employee-service/sections/<int:section_id>/", EmployeeServiceSectionDetailApiView.as_view()),
    path("employee-service/media-proxy/", EmployeeServiceMediaProxyApiView.as_view()),
    path("employee-service/employees/", EmployeeServiceEmployeeListApiView.as_view()),
    path("employee-service/base-image-change-logs/", EmployeeServiceBaseImageChangeLogListApiView.as_view()),
    path("employee-service/base-image-change-logs/<int:log_id>/", EmployeeServiceBaseImageChangeLogDetailApiView.as_view()),
    path("employee-service/employees/<slug:slug>/", EmployeeServiceEmployeeDetailApiView.as_view()),
]
