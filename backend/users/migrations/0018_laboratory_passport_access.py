from django.db import migrations, models


# Yangi maydonlarning model-darajadagi standarti eng kam huquq (False). Bazada esa
# rollar allaqachon mavjud — ularga migratsiya paytida hozirgi xulqqa mos qiymat
# yozilmasa, админ паспорт yaratish huquqini, СТТЛ esa «На подписи мне» ni yo'qotardi.
PENDING_APPROVAL_ROLES = {'admin', 'sttl_head', 'czl_head', 'dispatcher'}
PASSPORT_CREATE_ROLES = {'admin', 'shift_head'}
PASSPORT_DELETE_ROLES = {'admin'}
PASSPORT_EDIT_ROLES = {'admin', 'it_center', 'shift_head', 'sttl_head', 'czl_head', 'dispatcher'}


def backfill_existing_roles(apps, schema_editor):
    RolePageAccess = apps.get_model('users', 'RolePageAccess')
    updated_fields = [
        'can_view_pending_approvals',
        'can_view_spravki',
        'can_create_passport',
        'can_edit_passport',
        'can_delete_passport',
        'can_create_spravka',
    ]
    for row in RolePageAccess.objects.all():
        role = str(row.role or '').strip().lower()
        row.can_view_pending_approvals = role in PENDING_APPROVAL_ROLES
        # «Справки» ilgari hech qanday tekshiruvsiz hammaga ochiq edi.
        row.can_view_spravki = True
        row.can_create_passport = role in PASSPORT_CREATE_ROLES
        row.can_edit_passport = role in PASSPORT_EDIT_ROLES
        row.can_delete_passport = role in PASSPORT_DELETE_ROLES
        row.can_create_spravka = role in PASSPORT_CREATE_ROLES
        row.save(update_fields=updated_fields)


def noop_reverse(apps, schema_editor):
    """Maydonlar o'chirilgani uchun qaytarishda alohida ish kerak emas."""


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_customrole'),
    ]

    operations = [
        migrations.AddField(
            model_name='rolepageaccess',
            name='can_view_pending_approvals',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='rolepageaccess',
            name='can_view_spravki',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='rolepageaccess',
            name='can_create_passport',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='rolepageaccess',
            name='can_edit_passport',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='rolepageaccess',
            name='can_delete_passport',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='rolepageaccess',
            name='can_create_spravka',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(backfill_existing_roles, noop_reverse),
    ]
