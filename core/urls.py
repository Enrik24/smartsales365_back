# core/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="SmartSales365 API",
        default_version='v1',
        description="Sistema Inteligente de Gestión Comercial y Reportes Dinámicos",
        terms_of_service="https://www.smartsales365.com/terms/",
        contact=openapi.Contact(email="soporte@smartsales365.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API Routes
    path('api/auth/', include('users.urls')),
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/ai/', include('ai_models.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/voice-commands/', include('voice_commands.urls')),
    path('api/system/', include('system.urls')),  # ✅ AÑADIR
]