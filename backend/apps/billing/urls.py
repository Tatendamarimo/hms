from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InvoiceDetailView,
    PaymentCreateView,
    ServiceItemViewSet,
    ServicePriceViewSet,
)

router = DefaultRouter()
router.register("catalog", ServiceItemViewSet, basename="catalog")
router.register("prices", ServicePriceViewSet, basename="prices")

urlpatterns = [
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<int:pk>/payments/", PaymentCreateView.as_view(), name="invoice-payments"),
    *router.urls,
]
