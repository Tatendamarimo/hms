from django.urls import path

from . import print_views

urlpatterns = [
    path("registration/<int:pk>/", print_views.registration, name="print-registration"),
]
