from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth (allauth)
    path('accounts/', include('allauth.urls')),

    # Public journal site
    path('', include('apps.journal.urls')),

    # Author portal
    path('author/', include('apps.submissions.urls')),

    # Editorial dashboard
    path('editorial/', include('apps.editorial.urls')),

    # Reviewer workspace
    path('review/', include('apps.reviews.urls')),

    # REST API
    path('api/v1/', include('apps.api.urls')),

    # Accounts (profile)
    path('author/', include('apps.accounts.urls')),

    # Journal admin (custom platform admin — not Django admin)
    path('journal-admin/', include('apps.accounts.admin_urls')),

    # Notifications
    path('notifications/', include('apps.notifications.urls')),

    # Reviewer invitation magic links
    path('review/', include('apps.reviewers.urls')),

    # Production
    path('production/', include('apps.production.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
