from rest_framework.routers import DefaultRouter

from .views import (
    RiftboundCardViewSet, RiftboundSetViewSet, RiftboundFormatViewSet,
    RiftboundBanlistViewSet, RiftboundIconViewSet,
    RiftboundDeckViewSet, RiftboundCollectionViewSet, RiftboundWishlistViewSet,
)

router = DefaultRouter()
router.register(r"cards", RiftboundCardViewSet, basename="riftbound-card")
router.register(r"sets", RiftboundSetViewSet, basename="riftbound-set")
router.register(r"formats", RiftboundFormatViewSet, basename="riftbound-format")
router.register(r"banlist", RiftboundBanlistViewSet, basename="riftbound-banlist")
router.register(r"icons", RiftboundIconViewSet, basename="riftbound-icon")
router.register(r"decks", RiftboundDeckViewSet, basename="riftbound-deck")
router.register(r"collection", RiftboundCollectionViewSet, basename="riftbound-collection")
router.register(r"wishlist", RiftboundWishlistViewSet, basename="riftbound-wishlist")

urlpatterns = router.urls
