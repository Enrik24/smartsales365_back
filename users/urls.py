# users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('registro/', views.registro_usuario, name='registro'),
    path('login/', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Gestión de contraseñas
    path('cambiar-password/', views.cambiar_password, name='cambiar_password'),
    path('recuperar-password/', views.recuperar_password, name='recuperar_password'),
    
    # Gestión de usuarios
    path('usuarios/', views.UsuarioListView.as_view(), name='lista_usuarios'),
    path('clientes/', views.ClienteListView.as_view(), name='lista_clientes'),
    path('usuarios/<pk>/', views.UsuarioDetailView.as_view(), name='detalle_usuario'),
    path('usuarios/me/', views.UsuarioDetailView.as_view(), name='mi_perfil'), # Debe ir antes que <pk> si pk no es int
    path('usuarios/me/roles/', views.obtener_mis_roles, name='mis_roles'),
    
    # Roles y permisos
    path('roles/', views.RolListCreateView.as_view(), name='lista_roles'),
    path('roles/<int:pk>/', views.RolDetailView.as_view(), name='detalle_rol'),
    path('permisos/', views.PermisoListCreateView.as_view(), name='lista_permisos'),
    path('permisos/<int:pk>/', views.PermisoDetailView.as_view(), name='detalle_permiso'),
    path('usuario-roles/', views.UsuarioRolListCreateView.as_view(), name='usuario_roles'),
    path('rol-permisos/', views.RolPermisoListCreateView.as_view(), name='rol_permisos'),

    # Nuevos endpoints de gestión de permisos
    path('asignar-rol/', views.asignar_rol_usuario, name='asignar_rol'),
    path('revocar-rol/', views.revocar_rol_usuario, name='revocar_rol'),
    path('usuarios/<int:usuario_id>/roles/', views.obtener_roles_usuario, name='roles_usuario'),
    path('usuarios/<int:usuario_id>/verificar-permiso/', views.verificar_permiso_usuario, name='verificar_permiso'),
    path('usuarios/<int:usuario_id>/desactivar/', views.desactivar_usuario, name='desactivar_usuario'),
    path('usuarios/<int:usuario_id>/activar/', views.activar_usuario, name='activar_usuario'),
]