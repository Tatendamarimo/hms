from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConsultationViewSet, DiagnosisViewSet, EncounterConsultationView

router = DefaultRouter()
router.register("consultations", ConsultationViewSet, basename="consultations")
router.register("diagnoses", DiagnosisViewSet, basename="diagnoses")

urlpatterns = [
    path(
        "encounters/<int:pk>/consultation/",
        EncounterConsultationView.as_view(),
        name="encounter-consultation",
    ),
    *router.urls,
]
