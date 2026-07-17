from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InvoiceDetailView,
    InvoiceItemCreateView,
    InvoiceItemVoidView,
    PaymentCreateView,
    PaymentReverseView,
    ServiceItemViewSet,
    ServicePriceViewSet,
)

router = DefaultRouter()
router.register("catalog", ServiceItemViewSet, basename="catalog")
router.register("prices", ServicePriceViewSet, basename="prices")

urlpatterns = [
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<int:pk>/payments/", PaymentCreateView.as_view(), name="invoice-payments"),
    path("invoices/<int:pk>/items/", InvoiceItemCreateView.as_view(), name="invoice-items"),
    path(
        "invoices/<int:pk>/items/<int:item_pk>/void/",
        InvoiceItemVoidView.as_view(),
        name="invoice-item-void",
    ),
    path("payments/<int:pk>/reverse/", PaymentReverseView.as_view(), name="payment-reverse"),
    *router.urls,
]
