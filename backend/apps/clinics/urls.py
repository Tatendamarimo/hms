from django.urls import path

from .views import MyClinicsView, PublicBrandingView

urlpatterns = [
    path("mine/", MyClinicsView.as_view(), name="my-clinics"),
    path("branding/", PublicBrandingView.as_view(), name="public-branding"),
]
