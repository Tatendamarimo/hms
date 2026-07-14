from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EncounterViewSet, PatientTimelineView

router = DefaultRouter()
router.register("encounters", EncounterViewSet, basename="encounters")

urlpatterns = [
    path("patients/<int:pk>/timeline/", PatientTimelineView.as_view(), name="patient-timeline"),
    *router.urls,
]
