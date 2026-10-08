"""
base app modellari.

СИЗ (PPE) quyi tizimi loyihadan olib tashlandi: PPEProduct, PPEArrival, Item,
PendingItemIssue, DepartmentPPERenewalRule, PositionPPERenewalRule va
EmployeeFaceIdOverride modellari hamda ularning jadvallari o'chirildi
(migratsiya 0038).

Bu yerda faqat pasport oqimi tayanadigan ma'lumotnomalar qoldi. Ulardan eng
muhimi — ResponsiblePerson: passports_app/approval.py imzolovchini aynan shu
jadvaldan topadi.
"""

from django.contrib.auth.models import User
from django.db import models
from django.template.defaultfilters import slugify
from simple_history.models import HistoricalRecords

from base.middleware import CurrentUserMiddleware

class Department(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название цеха')
    boss_fullName = models.CharField(max_length=255, verbose_name='Руководитель цеха')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Цех '
        verbose_name_plural = 'Цех'

class Section(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='Название цеха')
    name = models.CharField(max_length=255, verbose_name='Название отдела')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отдел'
        db_table = 'base_section'

class ResponsiblePerson(models.Model):
    full_name = models.CharField(max_length=255, verbose_name='ФИО ответственного лица')
    position = models.CharField(max_length=255, verbose_name='Должность ответственного лица')
    employee_slug = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name='Slug сотрудника (employee_service)',
    )

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Ответственное лицо'
        verbose_name_plural = 'Ответственные лица'

class Employee(models.Model):
    first_name = models.CharField(max_length=255, verbose_name='Имя')
    last_name = models.CharField(max_length=255, verbose_name='Фамилия')
    surname = models.CharField(max_length=255, verbose_name='Отчество')
    tabel_number = models.CharField(max_length=255, unique=True, verbose_name='Табельный номер')
    
    gender = models.CharField(choices=[('M', 'Мужской'), ('F', 'Женский')], max_length=255, verbose_name='Пол')
    height = models.CharField(max_length=255, verbose_name='Рост')
    
    clothe_size = models.CharField(max_length=255, verbose_name='Размер одежды')
    shoe_size = models.CharField(max_length=255, verbose_name='Размер обуви')
    base_image = models.ImageField(upload_to='employee_base_images/', null=True, blank=True, verbose_name='Базовое фото 3x4')
    
    section = models.ForeignKey(Section, on_delete=models.CASCADE, verbose_name='Отдел')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='Цех')
    position = models.TextField(verbose_name='Должность', blank=True, null=True)
    date_of_employment = models.DateField(verbose_name='Дата приема на работу', blank=True, null=True)
    date_of_change_position = models.DateField(verbose_name='Дата последнего изменения должности', blank=True, null=True)
    
    addedUser = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="Сотрудник", null=True, blank=True)
    updatedUser = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="updated_items",
                                    verbose_name="Изменил", null=True, blank=True)
    updatedAt = models.DateTimeField(auto_now=True, verbose_name="Дата изменения", null=True, blank=True)
    
    slug = models.SlugField(unique=True, blank=True)
    isActive = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
        inherit=True,
        excluded_fields=['tabel_number'] )
    def __str__(self):
        return self.first_name + " " + self.last_name + " " + self.surname

    def save(self, *args, **kwargs):
        user = CurrentUserMiddleware.get_current_user()
        if user and user.is_authenticated:
            self.updatedUser = user
            if not hasattr(self, '_history_user'):
                self._history_user = user

        if not self.slug:
            slug_parts = [self.tabel_number, self.first_name, self.last_name]
            base_slug = slugify("-".join(str(part).strip() for part in slug_parts if part))
            if not base_slug:
                base_slug = f"employee-{self.tabel_number}" if self.tabel_number else "employee"

            slug_candidate = base_slug
            counter = 1
            while Employee.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                counter += 1
                slug_candidate = f"{base_slug}-{counter}"

            self.slug = slug_candidate

        super().save(*args, **kwargs) 

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудник'
        db_table = 'base_employee'
