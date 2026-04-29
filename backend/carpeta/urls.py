from django.urls import path
from . import views

urlpatterns = [
    # Binder profile
    path("profile/", views.binder_profile_view, name="binder-profile"),
    path("profile/avatar/", views.upload_binder_avatar, name="binder-avatar"),
    # Collection
    path("collection/", views.MyCollectionListView.as_view(), name="collection-list"),
    path("collection/upsert/", views.collection_upsert, name="collection-upsert"),
    path("collection/batch-upsert/", views.collection_batch_upsert, name="collection-batch-upsert"),
    path("collection/bulk-import/", views.collection_bulk_import, name="collection-bulk-import"),
    path("collection/<int:card_id>/", views.collection_delete, name="collection-delete"),
    # Wishlist
    path("wishlist/", views.MyWishlistListView.as_view(), name="wishlist-list"),
    path("wishlist/toggle/", views.wishlist_toggle, name="wishlist-toggle"),
    path("wishlist/<int:card_id>/", views.wishlist_update, name="wishlist-update"),
    # Bulk IDs
    path("ids/", views.my_ids, name="carpeta-ids"),
    # Share token
    path("share-token/", views.my_share_token, name="share-token"),
    path("share-token/regenerate/", views.regenerate_share_token, name="share-token-regen"),
    # Collection stats
    path("stats/", views.collection_stats, name="collection-stats"),
    # Public stores
    path("stores/", views.PublicStoreIndexView.as_view(), name="public-stores-index"),
    path("store/<str:token>/", views.PublicStoreListView.as_view(), name="public-store"),
]
