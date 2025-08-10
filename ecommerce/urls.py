from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Swagger Documentation Dependancies
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # App urls
    path('api/', include('store.urls')),
    path('api/', include('users.urls')),


    path('api-auth/', include('rest_framework.urls')),

    # API Documentation with Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
