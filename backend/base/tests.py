"""
base app testlari.

СИЗ (PPE) testlari quyi tizim bilan birga olib tashlandi. Qolganlari
employee_service proksi qatlamini tekshiradi.
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from requests import RequestException

from .employee_data import build_employee_snapshot
from users.models import UserRole


class EmployeeServiceEmployeeBaseImagePermissionTests(APITestCase):
	def setUp(self):
		self.employee_slug = 'remote-employee-1'
		self.url = f'/api/v1/employee-service/employees/{self.employee_slug}/'
		self.admin_user = User.objects.create_user(username='admin_user', password='test12345')
		self.staff_user = User.objects.create_user(username='shift_head_user', password='test12345')
		self.it_center_user = User.objects.create_user(username='it_center_user', password='test12345')

		admin_profile, _ = UserRole.objects.get_or_create(user=self.admin_user)
		admin_profile.role = UserRole.ADMIN
		admin_profile.save(update_fields=['role'])

		staff_profile, _ = UserRole.objects.get_or_create(user=self.staff_user)
		staff_profile.role = UserRole.SHIFT_HEAD
		staff_profile.save(update_fields=['role'])

		it_center_profile, _ = UserRole.objects.get_or_create(user=self.it_center_user)
		it_center_profile.role = UserRole.IT_CENTER
		it_center_profile.save(update_fields=['role'])

	def _build_upload(self, name='avatar.png'):
		return SimpleUploadedFile(name, b'fake-image-bytes', content_type='image/png')

	@patch('base.employee_service_views.is_employee_service_enabled', return_value=True)
	@patch('base.employee_service_views.update_employee_base_image')
	def test_admin_can_update_employee_base_image(self, update_employee_base_image_mock, _enabled_mock):
		update_employee_base_image_mock.return_value = {
			'id': 1,
			'slug': self.employee_slug,
			'first_name': 'Ali',
			'base_image': '/media/employee_base_images/new-avatar.png',
			'base_image_url': '/media/employee_base_images/new-avatar.png',
		}

		self.client.force_authenticate(user=self.admin_user)
		response = self.client.put(self.url, {'base_image': self._build_upload()}, format='multipart')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['base_image_url'], '/media/employee_base_images/new-avatar.png')
		update_employee_base_image_mock.assert_called_once()
		self.assertEqual(update_employee_base_image_mock.call_args.args[0], self.employee_slug)
		self.assertEqual(update_employee_base_image_mock.call_args.args[1].name, 'avatar.png')
		self.assertEqual(update_employee_base_image_mock.call_args.kwargs['actor_username'], 'admin_user')
		self.assertEqual(update_employee_base_image_mock.call_args.kwargs['actor_role'], UserRole.ADMIN)

	@patch('base.employee_service_views.is_employee_service_enabled', return_value=True)
	@patch('base.employee_service_views.update_employee_base_image')
	def test_shift_head_can_update_employee_base_image(self, update_employee_base_image_mock, _enabled_mock):
		update_employee_base_image_mock.return_value = {
			'id': 1,
			'slug': self.employee_slug,
			'base_image': '/media/employee_base_images/staff-avatar.png',
			'base_image_url': '/media/employee_base_images/staff-avatar.png',
		}

		self.client.force_authenticate(user=self.staff_user)
		response = self.client.put(self.url, {'base_image': self._build_upload('staff.png')}, format='multipart')

		self.assertEqual(response.status_code, 200)
		update_employee_base_image_mock.assert_called_once()

	@patch('base.employee_service_views.is_employee_service_enabled', return_value=True)
	@patch('base.employee_service_views.update_employee_base_image')
	def test_it_center_cannot_update_employee_base_image(self, update_employee_base_image_mock, _enabled_mock):
		self.client.force_authenticate(user=self.it_center_user)
		response = self.client.put(self.url, {'base_image': self._build_upload('blocked.png')}, format='multipart')

		self.assertEqual(response.status_code, 403)
		update_employee_base_image_mock.assert_not_called()

class EmployeeServiceBaseImageChangeLogAccessTests(APITestCase):
	def setUp(self):
		self.url = '/api/v1/employee-service/base-image-change-logs/'
		self.admin_user = User.objects.create_user(username='admin_report_user', password='test12345')
		self.manager_user = User.objects.create_user(username='shift_head_report', password='test12345')
		self.plain_user = User.objects.create_user(username='plain_user_report', password='test12345')

		admin_profile, _ = UserRole.objects.get_or_create(user=self.admin_user)
		admin_profile.role = UserRole.ADMIN
		admin_profile.save(update_fields=['role'])

		manager_profile, _ = UserRole.objects.get_or_create(user=self.manager_user)
		manager_profile.role = UserRole.SHIFT_HEAD
		manager_profile.save(update_fields=['role'])

		plain_profile, _ = UserRole.objects.get_or_create(user=self.plain_user)
		plain_profile.role = UserRole.USER
		plain_profile.save(update_fields=['role'])

	@patch('base.employee_service_views.is_employee_service_enabled', return_value=True)
	@patch('base.employee_service_views.list_employee_base_image_change_logs')
	def test_admin_can_list_employee_base_image_change_logs(self, list_logs_mock, _enabled_mock):
		list_logs_mock.return_value = {
			'count': 1,
			'next': None,
			'previous': None,
			'results': [
				{
					'id': 7,
					'employee_slug': 'default-5413-a',
					'employee_full_name': 'Matruf Shabonov',
					'employee_tabel_number': '5413',
					'changed_by_username': 'warehouse_user',
					'changed_by_user_id': '42',
					'changed_by_role': 'shift_head',
					'old_image': 'employee_base_images/old.jpg',
					'old_image_url': '/media/employee_base_images/old.jpg',
					'new_image': 'employee_base_images/new.jpg',
					'new_image_url': '/media/employee_base_images/new.jpg',
					'created_at': '2026-04-30T10:15:00Z',
				}
			],
		}

		self.client.force_authenticate(user=self.admin_user)
		response = self.client.get(self.url, {'search': '5413'})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 1)
		self.assertEqual(
			response.data['results'][0]['new_image_url'],
			'/api/v1/employee-service/media-proxy/?path=%2Fmedia%2Femployee_base_images%2Fnew.jpg',
		)
		list_logs_mock.assert_called_once_with(
			search='5413',
			changed_by_username=None,
			employee_slug=None,
			date_from=None,
			date_to=None,
			page=None,
			page_size=None,
		)

	@patch('base.employee_service_views.is_employee_service_enabled', return_value=True)
	@patch('base.employee_service_views.list_employee_base_image_change_logs', return_value={'count': 0, 'next': None, 'previous': None, 'results': []})
	def test_shift_head_can_list_employee_base_image_change_logs(self, list_logs_mock, _enabled_mock):
		self.client.force_authenticate(user=self.manager_user)
		response = self.client.get(self.url)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['count'], 0)
		list_logs_mock.assert_called_once()

	@patch('base.employee_service_views.is_employee_service_enabled', return_value=True)
	@patch('base.employee_service_views.list_employee_base_image_change_logs')
	def test_plain_user_cannot_list_employee_base_image_change_logs(self, list_logs_mock, _enabled_mock):
		self.client.force_authenticate(user=self.plain_user)
		response = self.client.get(self.url)

		self.assertEqual(response.status_code, 403)
		list_logs_mock.assert_not_called()

class EmployeeServiceMediaProxyTests(APITestCase):
	def test_build_employee_snapshot_rewrites_host_docker_internal_media_to_proxy_path(self):
		payload = build_employee_snapshot({
			'base_image': 'https://host.docker.internal:5000/media/employee_base_images/5413-a.jpg',
			'base_image_url': 'https://host.docker.internal:5000/media/employee_base_images/5413-a.jpg',
		})

		self.assertEqual(
			payload['base_image'],
			'/api/v1/employee-service/media-proxy/?path=%2Fmedia%2Femployee_base_images%2F5413-a.jpg',
		)
		self.assertEqual(
			payload['base_image_url'],
			'/api/v1/employee-service/media-proxy/?path=%2Fmedia%2Femployee_base_images%2F5413-a.jpg',
		)

	def test_build_employee_snapshot_preserves_employee_service_size_fields(self):
		payload = build_employee_snapshot({
			'special_clothing_size': '54',
			'clothe_size': '56',
			'shoe_size': '42',
			'jacket_size': '58',
			'tshirt_size': 'L',
		})

		self.assertEqual(payload['special_clothing_size'], '54')
		self.assertEqual(payload['clothe_size'], '56')
		self.assertEqual(payload['shoe_size'], '42')
		self.assertEqual(payload['jacket_size'], '58')
		self.assertEqual(payload['tshirt_size'], 'L')

	@patch('base.employee_service_views.requests.get')
	@patch('base.employee_service_views.settings')
	def test_media_proxy_falls_back_to_public_origin_when_internal_media_is_unavailable(self, settings_mock, requests_get_mock):
		settings_mock.EMPLOYEE_SERVICE_BASE_URL = 'http://employee-service:8010'
		settings_mock.EMPLOYEE_SERVICE_PUBLIC_URL = 'https://192.168.2.74:5001'
		settings_mock.EMPLOYEE_SERVICE_TIMEOUT = 15

		public_response = type('Response', (), {
			'status_code': 200,
			'content': b'image-bytes',
			'headers': {'Content-Type': 'image/jpeg', 'Cache-Control': 'max-age=60'},
		})()
		requests_get_mock.side_effect = [
			RequestException('internal media unavailable'),
			public_response,
		]

		response = self.client.get('/api/v1/employee-service/media-proxy/?path=%2Fmedia%2Femployee_base_images%2Fphoto.jpg')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.content, b'image-bytes')
		self.assertEqual(response['Content-Type'], 'image/jpeg')
		self.assertEqual(response['Cache-Control'], 'max-age=60')
		self.assertEqual(requests_get_mock.call_count, 2)
		self.assertEqual(requests_get_mock.call_args_list[0].args[0], 'http://employee-service:8010/media/employee_base_images/photo.jpg')
		self.assertEqual(requests_get_mock.call_args_list[1].args[0], 'https://192.168.2.74:5001/media/employee_base_images/photo.jpg')
