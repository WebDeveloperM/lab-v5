from django.contrib import admin

from .models import ResponsiblePerson

# СИЗ modellari (PPEProduct, PPEArrival, Item) loyihadan olib tashlandi,
# shuning uchun ularning admin ro'yxatdan o'tishi ham yo'q.
admin.site.register(ResponsiblePerson)
