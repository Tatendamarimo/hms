from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import healthz

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("clinics/", include("apps.clinics.urls")),
    path("billing/", include("apps.billing.urls")),
    path("", include("apps.patients.urls")),
    path("", include("apps.encounters.urls")),
    path("", include("apps.clinical.urls")),
    path("", include("apps.pharmacy.urls")),
    path("", include("apps.laboratory.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

print_urls = [
    path("", include("apps.patients.print_urls")),
    path("", include("apps.clinical.print_urls")),
    path("", include("apps.laboratory.print_urls")),
    path("", include("apps.billing.print_urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("print/", include(print_urls)),
    path("healthz/", healthz, name="healthz"),
]
