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
    RiftboundMyPurchaseOrderListView,
    riftbound_my_order_assignments,
    riftbound_accept_store_order, riftbound_cancel_store_order,
    riftbound_workspaces,
    riftbound_tours,
    riftbound_workspace_permissions,
    riftbound_workspace_permission_upsert,
    riftbound_workspace_permission_update,
    riftbound_workspace_permission_delete,
    tcgplayer_price_view, tcgplayer_prices_batch_view,
    tcgmatch_price_view,
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
    path("workspaces/", riftbound_workspaces, name="riftbound-workspaces"),
    path("tours/", riftbound_tours, name="riftbound-tours"),
    path("workspaces/<int:profile_id>/permissions/", riftbound_workspace_permissions, name="riftbound-workspace-permissions"),
    path("workspaces/<int:profile_id>/permissions/upsert/", riftbound_workspace_permission_upsert, name="riftbound-workspace-permission-upsert"),
    path("workspaces/<int:profile_id>/permissions/<int:permission_id>/", riftbound_workspace_permission_update, name="riftbound-workspace-permission-update"),
    path("workspaces/<int:profile_id>/permissions/<int:permission_id>/delete/", riftbound_workspace_permission_delete, name="riftbound-workspace-permission-delete"),
    path("stores/", RiftboundPublicStoreIndexView.as_view(), name="riftbound-public-stores"),
    path("store/<str:token>/", RiftboundPublicStoreListView.as_view(), name="riftbound-public-store"),
    path("store/<str:token>/orders/", RiftboundPublicStoreOrderCreateView.as_view(), name="riftbound-public-store-orders"),
    path("wishlist-public/<str:token>/", RiftboundPublicWishlistListView.as_view(), name="riftbound-public-wishlist"),
    path("orders/mine/", RiftboundMyStoreOrderListView.as_view(), name="riftbound-my-store-orders"),
    path("orders/mine/purchases/", RiftboundMyPurchaseOrderListView.as_view(), name="riftbound-my-purchase-orders"),
    path("orders/mine/assigned-summary/", riftbound_my_order_assignments, name="riftbound-my-store-order-assignments"),
    path("orders/<int:order_id>/accept/", riftbound_accept_store_order, name="riftbound-accept-store-order"),
    path("orders/<int:order_id>/cancel/", riftbound_cancel_store_order, name="riftbound-cancel-store-order"),
    path("tcgplayer/price/", tcgplayer_price_view, name="riftbound-tcgplayer-price"),
    path("tcgplayer/prices-batch/", tcgplayer_prices_batch_view, name="riftbound-tcgplayer-prices-batch"),
    path("tcgmatch/price/", tcgmatch_price_view, name="riftbound-tcgmatch-price"),
] + router.urls
