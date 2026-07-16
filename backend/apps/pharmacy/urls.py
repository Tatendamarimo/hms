from rest_framework.routers import DefaultRouter

from .views import MedicationViewSet

router = DefaultRouter()
router.register("medications", MedicationViewSet, basename="medications")

urlpatterns = router.urls
