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
    tcgplayer_price_view, tcgplayer_prices_batch_view,
    riftcodex_sync_status_view,
    riftcodex_index_proxy_view, riftcodex_audit_status_view,
    riftcodex_run_sync_view, riftcodex_run_audit_view, riftcodex_audit_export_csv_view,
    riftcodex_ops_overview_view,
    riftcodex_ops_run_detail_view, riftcodex_ops_rerun_view,
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
    path("tcgplayer/price/", tcgplayer_price_view, name="riftbound-tcgplayer-price"),
    path("tcgplayer/prices-batch/", tcgplayer_prices_batch_view, name="riftbound-tcgplayer-prices-batch"),
    path("sync/status/", riftcodex_sync_status_view, name="riftbound-riftcodex-sync-status"),
    path("index/<str:index_type>/", riftcodex_index_proxy_view, name="riftbound-riftcodex-index-proxy"),
    path("audit/status/", riftcodex_audit_status_view, name="riftbound-riftcodex-audit-status"),
    path("ops/run-sync/", riftcodex_run_sync_view, name="riftbound-riftcodex-run-sync"),
    path("ops/run-audit/", riftcodex_run_audit_view, name="riftbound-riftcodex-run-audit"),
    path("ops/overview/", riftcodex_ops_overview_view, name="riftbound-riftcodex-ops-overview"),
    path("ops/runs/<int:run_id>/", riftcodex_ops_run_detail_view, name="riftbound-riftcodex-ops-run-detail"),
    path("ops/runs/<int:run_id>/rerun/", riftcodex_ops_rerun_view, name="riftbound-riftcodex-ops-rerun"),
    path("audit/export.csv", riftcodex_audit_export_csv_view, name="riftbound-riftcodex-audit-export-csv"),
] + router.urls
