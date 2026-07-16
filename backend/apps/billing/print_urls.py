from django.urls import path

from . import print_views

urlpatterns = [
    path("invoice/<int:pk>/", print_views.invoice, name="print-invoice"),
    path("receipt/<int:pk>/", print_views.receipt, name="print-receipt"),
]
