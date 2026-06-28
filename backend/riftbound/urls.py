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
    RiftboundPublicStoreOrderCreateView, RiftboundMyStoreOrderListView,
    riftbound_my_order_assignments,
    riftbound_accept_store_order, riftbound_cancel_store_order,
    tcgplayer_price_view, tcgplayer_prices_batch_view,
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
    path("store/<str:token>/orders/", RiftboundPublicStoreOrderCreateView.as_view(), name="riftbound-public-store-orders"),
    path("wishlist-public/<str:token>/", RiftboundPublicWishlistListView.as_view(), name="riftbound-public-wishlist"),
    path("orders/mine/", RiftboundMyStoreOrderListView.as_view(), name="riftbound-my-store-orders"),
    path("orders/mine/assigned-summary/", riftbound_my_order_assignments, name="riftbound-my-store-order-assignments"),
    path("orders/<int:order_id>/accept/", riftbound_accept_store_order, name="riftbound-accept-store-order"),
    path("orders/<int:order_id>/cancel/", riftbound_cancel_store_order, name="riftbound-cancel-store-order"),
    path("tcgplayer/price/", tcgplayer_price_view, name="riftbound-tcgplayer-price"),
    path("tcgplayer/prices-batch/", tcgplayer_prices_batch_view, name="riftbound-tcgplayer-prices-batch"),
] + router.urls
