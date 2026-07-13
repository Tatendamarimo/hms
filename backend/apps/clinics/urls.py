from django.urls import path

from .views import MyClinicsView

urlpatterns = [
    path("mine/", MyClinicsView.as_view(), name="my-clinics"),
]
