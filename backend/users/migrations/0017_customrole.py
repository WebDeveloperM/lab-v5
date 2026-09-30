from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_rolepageaccess_can_view_passports'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(max_length=32, unique=True, verbose_name='Ключ роли')),
                ('label', models.CharField(max_length=64, verbose_name='Название роли')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Дополнительная роль',
                'verbose_name_plural': 'Дополнительные роли',
                'ordering': ['label', 'key'],
            },
        ),
    ]
