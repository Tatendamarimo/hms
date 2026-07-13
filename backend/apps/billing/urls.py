from rest_framework.routers import DefaultRouter

from .views import ServiceItemViewSet, ServicePriceViewSet

router = DefaultRouter()
router.register("catalog", ServiceItemViewSet, basename="catalog")
router.register("prices", ServicePriceViewSet, basename="prices")

urlpatterns = router.urls
