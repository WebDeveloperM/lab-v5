"""
base app — laboratoriya pasport tizimi uchun qolgan yordamchi qism.

СИЗ (PPE) quyi tizimi loyihadan butunlay olib tashlandi. Bu faylda faqat
pasport oqimi hali tayanadigan narsalar qoldi:

  * ResponsiblePerson sozlamalari — passports_app/approval.py imzolovchini
    aynan shu ma'lumotnomadan topadi;
  * Department / Section sozlamalari — employee_service dagi ma'lumotnomalar ustidan proksi;
  * ensure_can_modify — passports_app/views.py import qiladi;
  * yuz-tanish funksiyalari — users/views.py login paytidagi Face ID tasdig'i uchun
    calculate_face_identity_similarity / calculate_face_similarity ni chaqiradi.
"""

import os
from functools import lru_cache

import numpy as np
import requests
from PIL import Image

from django.conf import settings
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.authentication import ExpiringTokenAuthentication as TokenAuthentication
from users.models import UserRole, get_effective_user_role

from .models import ResponsiblePerson
from .serializers import ResponsiblePersonSerializer
from .employee_service_client import (
    EmployeeServiceClientError,
    create_department,
    create_section,
    delete_department,
    delete_section,
    list_departments,
    list_sections,
    update_department,
    update_section,
)


FACE_MODEL_DIR = os.path.join(settings.BASE_DIR, 'base', 'ml_models')
YUNET_MODEL_FILENAME = 'face_detection_yunet_2023mar.onnx'
SFACE_MODEL_FILENAME = 'face_recognition_sface_2021dec.onnx'
YUNET_MODEL_URL = 'https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'
SFACE_MODEL_URL = 'https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx'

def extract_service_results(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ['results', 'data', 'items']:
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []

def normalize_department_payload(department):
    return {
        'id': department.get('id'),
        'name': department.get('name', ''),
        'boss_fullName': department.get('boss_full_name', department.get('boss_fullName', '')),
        'sort_order': department.get('sort_order', 0) or 0,
    }

def department_sort_key(item):
    sort_order = item.get('sort_order')
    normalized_sort_order = sort_order if isinstance(sort_order, int) and sort_order > 0 else 10 ** 9
    return (normalized_sort_order, (item.get('name') or '').lower())

def normalize_section_payload(section):
    department = section.get('department') or {}
    return {
        'id': section.get('id'),
        'department': section.get('department_id', department.get('id')),
        'department_name': section.get('department_name', department.get('name', '')),
        'name': section.get('name', ''),
    }

def build_department_service_payload(data):
    payload = {}
    if 'name' in data:
        payload['name'] = str(data.get('name', '')).strip()
    if 'boss_fullName' in data or 'boss_full_name' in data:
        payload['boss_full_name'] = str(data.get('boss_full_name', data.get('boss_fullName', ''))).strip()
    return payload

def build_section_service_payload(data):
    payload = {}
    if 'name' in data:
        payload['name'] = str(data.get('name', '')).strip()
    if 'department' in data or 'department_id' in data:
        payload['department_id'] = data.get('department_id', data.get('department'))
    return payload

def ensure_can_modify(request):
    """
    Проверяет, может ли пользователь модифицировать данные (кроме сотрудников).
    Разрешено: ADMIN, IT_CENTER, и роли из UserRole.MANAGER_TIER_ROLES
    Запрещено: USER
    """
    role = get_effective_user_role(request.user)
    if role in [UserRole.ADMIN, UserRole.IT_CENTER, *UserRole.MANAGER_TIER_ROLES]:
        return None
    return Response(
        {"error": "У вас есть только права на просмотр."},
        status=status.HTTP_403_FORBIDDEN,
    )

class SettingsDepartmentListCreateApiView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        try:
            departments = sorted(
                [normalize_department_payload(item) for item in extract_service_results(list_departments())],
                key=department_sort_key,
            )
        except EmployeeServiceClientError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(departments)

    def post(self, request):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        try:
            department = create_department(build_department_service_payload(request.data))
        except EmployeeServiceClientError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(normalize_department_payload(department), status=status.HTTP_201_CREATED)

class SettingsSectionListCreateApiView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        try:
            sections = sorted(
                [normalize_section_payload(item) for item in extract_service_results(list_sections())],
                key=lambda item: (item.get('name') or '').lower(),
            )
        except EmployeeServiceClientError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(sections)

    def post(self, request):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        try:
            section = create_section(build_section_service_payload(request.data))
        except EmployeeServiceClientError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(normalize_section_payload(section), status=status.HTTP_201_CREATED)

class SettingsResponsiblePersonListCreateApiView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        persons = ResponsiblePerson.objects.all().order_by(Lower('full_name'))
        serializer = ResponsiblePersonSerializer(persons, many=True)
        return Response(serializer.data)

    def post(self, request):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        serializer = ResponsiblePersonSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SettingsDepartmentDetailApiView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        try:
            department = update_department(pk, build_department_service_payload(request.data))
        except EmployeeServiceClientError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(normalize_department_payload(department))

    def delete(self, request, pk):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        try:
            delete_department(pk)
        except EmployeeServiceClientError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

class SettingsSectionDetailApiView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        try:
            section = update_section(pk, build_section_service_payload(request.data))
        except EmployeeServiceClientError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(normalize_section_payload(section))

    def delete(self, request, pk):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        try:
            delete_section(pk)
        except EmployeeServiceClientError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

class SettingsResponsiblePersonDetailApiView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        person = get_object_or_404(ResponsiblePerson, pk=pk)
        serializer = ResponsiblePersonSerializer(person, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        permission_error = ensure_can_modify(request)
        if permission_error:
            return permission_error

        person = get_object_or_404(ResponsiblePerson, pk=pk)
        person.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

def _load_cv2_module():
    try:
        import cv2  # type: ignore
        return cv2
    except Exception:
        return None

def _ensure_face_model_file(filename: str, url: str):
    os.makedirs(FACE_MODEL_DIR, exist_ok=True)
    model_path = os.path.join(FACE_MODEL_DIR, filename)
    if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
        return model_path, None

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        return None, f'Не удалось загрузить модель: {filename} ({exc})'

    try:
        with open(model_path, 'wb') as file_obj:
            file_obj.write(response.content)
    except Exception as exc:
        return None, f'Не удалось сохранить модель: {filename} ({exc})'

    return model_path, None

@lru_cache(maxsize=1)
def _get_sface_engines():
    cv2 = _load_cv2_module()
    if cv2 is None:
        return None, None, 'Не удалось загрузить OpenCV (cv2) модуль. Убедитесь, что он установлен и доступен.'  

    yunet_path, yunet_error = _ensure_face_model_file(YUNET_MODEL_FILENAME, YUNET_MODEL_URL)
    if yunet_error:
        return None, None, yunet_error

    sface_path, sface_error = _ensure_face_model_file(SFACE_MODEL_FILENAME, SFACE_MODEL_URL)
    if sface_error:
        return None, None, sface_error

    try:
        detector = cv2.FaceDetectorYN.create(yunet_path, '', (320, 320), 0.9, 0.3, 5000)
        recognizer = cv2.FaceRecognizerSF.create(sface_path, '')
        return detector, recognizer, None
    except Exception as exc:
        return None, None, f'SFace engine ishga tushmadi: {exc}'

def _extract_face_embedding(image: Image.Image):
    cv2 = _load_cv2_module()
    detector, recognizer, engine_error = _get_sface_engines()
    if cv2 is None or detector is None or recognizer is None:
        return None, engine_error or 'SFace engine mavjud emas'

    rgb_np = np.asarray(image.convert('RGB'))
    if rgb_np.size == 0:
        return None, 'Изображение пустое.'

    bgr = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR)
    height, width = bgr.shape[:2]
    if width < 20 or height < 20:
        return None, 'Размер изображения слишком мал.'

    detector.setInputSize((width, height))
    _, faces = detector.detect(bgr)
    if faces is None or len(faces) == 0:
        return None, 'Лицо не обнаружено'

    best_face = max(faces, key=lambda face: float(face[2]) * float(face[3]))
    try:
        aligned = recognizer.alignCrop(bgr, best_face)
        embedding = recognizer.feature(aligned)
    except Exception:
        return None, 'Не удалось вычислить вектор признаков лица'

    if embedding is None:
        return None, 'Не удалось вычислить вектор признаков лица'

    return embedding.astype(np.float32), None

def _embedding_similarity_percent(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
    vec_a = embedding_a.flatten().astype(np.float32)
    vec_b = embedding_b.flatten().astype(np.float32)

    denominator = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if denominator <= 1e-8:
        return 0.0

    cosine = float(np.dot(vec_a, vec_b) / denominator)
    percent = ((cosine + 1.0) / 2.0) * 100.0
    return max(0.0, min(100.0, percent))

@lru_cache(maxsize=1)
def _get_face_cascade_classifier():
    cv2 = _load_cv2_module()
    if cv2 is None:
        return None

    try:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        classifier = cv2.CascadeClassifier(cascade_path)
        if classifier.empty():
            return None
        return classifier
    except Exception:
        return None

def extract_primary_face(image: Image.Image):
    cv2 = _load_cv2_module()
    classifier = _get_face_cascade_classifier()
    if cv2 is None or classifier is None:
        return None

    rgb_np = np.asarray(image.convert('RGB'))
    if rgb_np.size == 0:
        return None

    gray = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)

    faces = classifier.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(64, 64),
    )
    if faces is None or len(faces) == 0:
        return None

    x, y, w, h = max(faces, key=lambda f: int(f[2]) * int(f[3]))

    left_trim = int(w * 0.08)
    right_trim = int(w * 0.08)
    top_trim = int(h * 0.05)
    bottom_trim = int(h * 0.12)

    x1 = max(0, int(x) + left_trim)
    y1 = max(0, int(y) + top_trim)
    x2 = min(gray.shape[1], int(x + w) - right_trim)
    y2 = min(gray.shape[0], int(y + h) - bottom_trim)

    if x2 <= x1 or y2 <= y1:
        return None

    face_gray = gray[y1:y2, x1:x2]
    if face_gray.size == 0:
        return None

    face_gray = cv2.resize(face_gray, (160, 160), interpolation=cv2.INTER_AREA)
    return face_gray

def _orb_similarity(face_a: np.ndarray, face_b: np.ndarray) -> float:
    cv2 = _load_cv2_module()
    if cv2 is None:
        return 0.0

    try:
        orb = cv2.ORB_create(nfeatures=400)
        keypoints_a, descriptors_a = orb.detectAndCompute(face_a, None)
        keypoints_b, descriptors_b = orb.detectAndCompute(face_b, None)

        if descriptors_a is None or descriptors_b is None:
            return 0.0
        if not keypoints_a or not keypoints_b:
            return 0.0

        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        knn_matches = matcher.knnMatch(descriptors_a, descriptors_b, k=2)

        good_matches = []
        for pair in knn_matches:
            if len(pair) < 2:
                continue
            first, second = pair
            if first.distance < 0.75 * second.distance:
                good_matches.append(first)

        denominator = max(len(keypoints_a), len(keypoints_b), 1)
        return max(0.0, min(1.0, len(good_matches) / float(denominator)))
    except Exception:
        return 0.0

def _ncc_similarity(face_a: np.ndarray, face_b: np.ndarray) -> float:
    a = face_a.astype(np.float32)
    b = face_b.astype(np.float32)

    a_centered = a - float(np.mean(a))
    b_centered = b - float(np.mean(b))

    denominator = float(np.linalg.norm(a_centered) * np.linalg.norm(b_centered))
    if denominator <= 1e-8:
        return 0.0

    ncc = float(np.sum(a_centered * b_centered) / denominator)
    return max(0.0, min(1.0, (ncc + 1.0) / 2.0))

def _gradient_similarity(face_a: np.ndarray, face_b: np.ndarray) -> float:
    grad_ax = np.diff(face_a.astype(np.float32), axis=1)
    grad_ay = np.diff(face_a.astype(np.float32), axis=0)
    grad_bx = np.diff(face_b.astype(np.float32), axis=1)
    grad_by = np.diff(face_b.astype(np.float32), axis=0)

    grad_a = np.concatenate([grad_ax.flatten(), grad_ay.flatten()])
    grad_b = np.concatenate([grad_bx.flatten(), grad_by.flatten()])

    denominator = float(np.linalg.norm(grad_a) * np.linalg.norm(grad_b))
    if denominator <= 1e-8:
        return 0.0

    similarity = float(np.dot(grad_a, grad_b) / denominator)
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))

def _hog_similarity(face_a: np.ndarray, face_b: np.ndarray) -> float:
    cv2 = _load_cv2_module()
    if cv2 is None:
        return 0.0

    try:
        resized_a = cv2.resize(face_a.astype(np.uint8), (64, 64), interpolation=cv2.INTER_AREA)
        resized_b = cv2.resize(face_b.astype(np.uint8), (64, 64), interpolation=cv2.INTER_AREA)

        hog = cv2.HOGDescriptor(
            _winSize=(64, 64),
            _blockSize=(16, 16),
            _blockStride=(8, 8),
            _cellSize=(8, 8),
            _nbins=9,
        )

        feature_a = hog.compute(resized_a)
        feature_b = hog.compute(resized_b)

        if feature_a is None or feature_b is None:
            return 0.0

        vec_a = feature_a.flatten().astype(np.float32)
        vec_b = feature_b.flatten().astype(np.float32)

        denominator = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
        if denominator <= 1e-8:
            return 0.0

        cosine = float(np.dot(vec_a, vec_b) / denominator)
        return max(0.0, min(1.0, (cosine + 1.0) / 2.0))
    except Exception:
        return 0.0

def calculate_face_identity_similarity(reference_image: Image.Image, captured_image: Image.Image) -> float:
    if reference_image is None or captured_image is None:
        return 0.0

    if _load_cv2_module() is None:
        raise ValueError('Сервис распознавания лиц пока не запущен (cv2)')

    reference_embedding, reference_embedding_error = _extract_face_embedding(reference_image)
    captured_embedding, captured_embedding_error = _extract_face_embedding(captured_image)

    if reference_embedding is None or captured_embedding is None:
        if reference_embedding is None and captured_embedding is None:
            raise ValueError(reference_embedding_error or captured_embedding_error or 'Лица на изображениях не обнаружены')
        if reference_embedding is None:
            raise ValueError(reference_embedding_error or 'Лицо на сохраненном изображении не обнаружено')
        raise ValueError(captured_embedding_error or 'Лицо на изображении с камеры не обнаружено')

    return _embedding_similarity_percent(reference_embedding, captured_embedding)

def calculate_face_similarity(reference_image: Image.Image, captured_image: Image.Image) -> float:
    if reference_image is None or captured_image is None:
        return 0.0

    if _load_cv2_module() is None:
        raise ValueError('Сервис распознавания лиц пока не запущен (cv2)')

    reference_embedding, reference_embedding_error = _extract_face_embedding(reference_image)
    captured_embedding, captured_embedding_error = _extract_face_embedding(captured_image)

    embedding_similarity = None
    if reference_embedding is not None and captured_embedding is not None:
        embedding_similarity = _embedding_similarity_percent(reference_embedding, captured_embedding)

    ref_face = extract_primary_face(reference_image)
    cap_face = extract_primary_face(captured_image)

    if ref_face is None or cap_face is None:
        if embedding_similarity is not None:
            return embedding_similarity
        if ref_face is None and cap_face is None:
            raise ValueError(reference_embedding_error or captured_embedding_error or 'Лица на изображениях не обнаружены')
        if ref_face is None:
            raise ValueError(reference_embedding_error or 'Лицо на сохраненном изображении не обнаружено')
        raise ValueError(captured_embedding_error or 'Лицо на изображении с камеры не обнаружено')

    ref_np = np.asarray(ref_face, dtype=np.float32)
    cap_np = np.asarray(cap_face, dtype=np.float32)

    ref_eq = ref_np.copy()
    cap_eq = cap_np.copy()
    cv2 = _load_cv2_module()
    if cv2 is not None:
        ref_eq = cv2.equalizeHist(ref_eq.astype(np.uint8)).astype(np.float32)
        cap_eq = cv2.equalizeHist(cap_eq.astype(np.uint8)).astype(np.float32)

    diff = np.abs(ref_eq - cap_eq)
    pixel_similarity = 1.0 - float(np.mean(diff) / 255.0)

    ref_hist, _ = np.histogram(ref_eq.flatten(), bins=64, range=(0, 256), density=True)
    cap_hist, _ = np.histogram(cap_eq.flatten(), bins=64, range=(0, 256), density=True)
    hist_distance = float(np.sum(np.abs(ref_hist - cap_hist)))
    hist_similarity = max(0.0, min(1.0, 1.0 - (hist_distance / 2.0)))

    ncc_similarity = _ncc_similarity(ref_eq, cap_eq)
    gradient_similarity = _gradient_similarity(ref_eq, cap_eq)
    hog_similarity = _hog_similarity(ref_eq, cap_eq)
    orb_similarity = _orb_similarity(ref_eq.astype(np.uint8), cap_eq.astype(np.uint8))

    combined_similarity = (
        (pixel_similarity * 0.10)
        + (hist_similarity * 0.07)
        + (ncc_similarity * 0.33)
        + (gradient_similarity * 0.22)
        + (hog_similarity * 0.18)
        + (orb_similarity * 0.10)
    )
    classic_similarity = max(0.0, min(1.0, combined_similarity)) * 100.0

    if embedding_similarity is None:
        return classic_similarity

    high_accuracy_similarity = (embedding_similarity * 0.80) + (classic_similarity * 0.20)
    return max(0.0, min(100.0, high_accuracy_similarity))
