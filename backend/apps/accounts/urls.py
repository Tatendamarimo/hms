from django.urls import path

from .views import CsrfView, LoginView, LogoutView, MeView, SwitchClinicView

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("clinic/", SwitchClinicView.as_view(), name="auth-switch-clinic"),
]
