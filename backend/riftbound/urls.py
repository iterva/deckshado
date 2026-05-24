from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    RiftboundCardViewSet, RiftboundSetViewSet, RiftboundFormatViewSet,
    RiftboundBanlistViewSet, RiftboundIconViewSet,
    RiftboundDeckViewSet, RiftboundCollectionViewSet, RiftboundWishlistViewSet,
    riftbound_binder_profile_view, riftbound_upload_binder_avatar,
    riftbound_regenerate_share_token, riftbound_my_share_token,
    RiftboundPublicStoreListView, RiftboundPublicStoreIndexView,
    RiftboundPublicWishlistListView,
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

urlpatterns = [
    path("profile/", riftbound_binder_profile_view, name="riftbound-binder-profile"),
    path("profile/avatar/", riftbound_upload_binder_avatar, name="riftbound-binder-avatar"),
    path("share-token/", riftbound_my_share_token, name="riftbound-share-token"),
    path("share-token/regenerate/", riftbound_regenerate_share_token, name="riftbound-share-token-regen"),
    path("stores/", RiftboundPublicStoreIndexView.as_view(), name="riftbound-public-stores"),
    path("store/<str:token>/", RiftboundPublicStoreListView.as_view(), name="riftbound-public-store"),
    path("wishlist-public/<str:token>/", RiftboundPublicWishlistListView.as_view(), name="riftbound-public-wishlist"),
] + router.urls
