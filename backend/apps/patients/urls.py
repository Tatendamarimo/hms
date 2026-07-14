from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BreakGlassView, PatientViewSet

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patients")

urlpatterns = [
    path("break-glass/", BreakGlassView.as_view(), name="break-glass"),
    *router.urls,
]
