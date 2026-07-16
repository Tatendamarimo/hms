from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConsultationLabOrdersView, LabOrderViewSet

router = DefaultRouter()
router.register("lab-orders", LabOrderViewSet, basename="lab-orders")

urlpatterns = [
    path(
        "consultations/<int:pk>/lab-orders/",
        ConsultationLabOrdersView.as_view(),
        name="consultation-lab-orders",
    ),
    *router.urls,
]
