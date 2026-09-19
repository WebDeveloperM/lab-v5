from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import UserRole

User = get_user_model()


class UserWithRoleCreationForm(UserCreationForm):
	role = forms.ChoiceField(choices=UserRole.ROLE_CHOICES, required=True, initial=UserRole.USER)
	base_avatar = forms.ImageField(required=False)
	face_id_required = forms.BooleanField(required=False, initial=True, label='Требуется Face ID при входе')

	class Meta(UserCreationForm.Meta):
		model = User
		fields = ("username", "first_name", "last_name", "role")

	def save(self, commit=True):
		user = super().save(commit=commit)
		if commit:
			role_value = self.cleaned_data.get("role", UserRole.USER)
			base_avatar = self.cleaned_data.get("base_avatar")
			profile, _ = UserRole.objects.get_or_create(user=user)
			if profile.role != role_value:
				profile.role = role_value
			profile.face_id_required = self.cleaned_data.get("face_id_required", True)
			if base_avatar:
				profile.base_avatar = base_avatar
			profile.save()
		return user


class UserWithRoleChangeForm(UserChangeForm):
	role = forms.ChoiceField(choices=UserRole.ROLE_CHOICES, required=True)
	base_avatar = forms.ImageField(required=False)
	face_id_required = forms.BooleanField(required=False, label='Требуется Face ID при входе')

	class Meta(UserChangeForm.Meta):
		model = User
		fields = "__all__"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		current_role = UserRole.USER
		if self.instance and self.instance.pk:
			profile = getattr(self.instance, 'role_profile', None)
			if profile and profile.role:
				current_role = profile.role
			elif self.instance.is_superuser:
				current_role = UserRole.ADMIN
		self.fields["role"].initial = current_role
		profile = getattr(self.instance, 'role_profile', None)
		if profile and profile.base_avatar:
			self.fields["base_avatar"].initial = profile.base_avatar
		self.fields["face_id_required"].initial = profile.face_id_required if profile else True

	def save(self, commit=True):
		user = super().save(commit=commit)
		if commit:
			role_value = self.cleaned_data.get("role", UserRole.USER)
			base_avatar = self.cleaned_data.get("base_avatar")
			profile, _ = UserRole.objects.get_or_create(user=user)
			if profile.role != role_value:
				profile.role = role_value
			profile.face_id_required = self.cleaned_data.get("face_id_required", True)
			if base_avatar:
				profile.base_avatar = base_avatar
			profile.save()
		return user


try:
	admin.site.unregister(User)
except admin.sites.NotRegistered:
	pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
	add_form = UserWithRoleCreationForm
	form = UserWithRoleChangeForm

	fieldsets = DjangoUserAdmin.fieldsets + (
		('Role', {'fields': ('role', 'base_avatar', 'face_id_required')}),
	)

	add_fieldsets = DjangoUserAdmin.add_fieldsets + (
		('Role', {'fields': ('role', 'base_avatar', 'face_id_required')}),
	)

	def save_model(self, request, obj, form, change):
		super().save_model(request, obj, form, change)
		role_value = form.cleaned_data.get("role", UserRole.USER)
		base_avatar = form.cleaned_data.get("base_avatar")
		profile, _ = UserRole.objects.get_or_create(user=obj)
		if profile.role != role_value:
			profile.role = role_value
		profile.face_id_required = form.cleaned_data.get("face_id_required", True)
		if base_avatar:
			profile.base_avatar = base_avatar
		profile.save()


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
	list_display = ('user', 'role')
	list_filter = ('role',)
	search_fields = ('user__username',)