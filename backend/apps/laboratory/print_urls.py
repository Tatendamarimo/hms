from django.urls import path

from . import print_views

urlpatterns = [
    path("lab-request/<int:pk>/", print_views.lab_request, name="print-lab-request"),
]
