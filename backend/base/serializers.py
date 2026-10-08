"""
base app serializerlari.

СИЗ (PPE) quyi tizimi bilan birga PPEProduct/PPEArrival/Item/Employee va norma
serializerlari olib tashlandi. Department va Section sozlamalari endi lokal
modellar emas, employee_service ustidan proksi ishlaydi (base/views.py), shuning
uchun ularning serializerlari ham kerak emas.
"""

from rest_framework import serializers

from .models import ResponsiblePerson

class ResponsiblePersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponsiblePerson
        fields = ["id", "full_name", "position", "employee_slug"]
