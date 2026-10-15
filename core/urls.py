"""
URL configuration for sistema_evaluacion project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rh import views  # <-- ESTA ES LA LÍNEA MÁGICA QUE FALTABA
from rh.admin import admin_site, procesar_evaluaciones_loading_view
from rh.views import probar_correo_view, CustomAdminLoginView, dashboard_modulos_view
urlpatterns = [

    path('', RedirectView.as_view(url='/admin/dashboard/', permanent=False)),
    path('redireccionar-login/', views.redireccionar_segun_rol, name='redireccionar_login'),
    path('probar-correo/', probar_correo_view, name='probar_correo'),

    path('reportes/', include('reportes.urls', namespace='reportes')),
    
    path('admin/login/', CustomAdminLoginView.as_view(), name='login'),
    path('admin/dashboard/', dashboard_modulos_view, name='dashboard_modulos'),
    
    # 🌟 REDIRECCIÓN: Si el usuario escribe /admin/ o /admin en la URL
    path('admin/', RedirectView.as_view(url='/admin/dashboard/', permanent=False)),

    path('admin/rh/dashboard/', admin_site.admin_view(admin_site.index), name='rh_dashboard'),

    path('admin/descargar-plantilla/<str:model_name>/', views.descargar_plantilla_excel, name='descargar_plantilla'),
    path('evaluaciones/asignacion-competencias/exportar/', views.exportar_competencias_excel, name='exportar_competencias_excel'),
    path('admin/resumen-evaluaciones/excel-detalle/', views.exportar_detalle_competencias_excel, name='exportar_detalle_competencias_excel'),    
    path('admin/resumen-evaluaciones/excel/', views.exportar_resumen_excel, name='exportar_resumen_excel'),
    path('admin/resumen-evaluaciones/', views.resumen_evaluaciones_view, name='resumen_evaluaciones'),    
    path('admin/panel-evaluacion/', views.panel_evaluacion_view, name='panel_evaluacion'),    
    path('admin/panel-evaluacion/<int:subordinado_id>/', views.panel_evaluacion_view, name='panel_evaluacion_subordinado'),
    path('admin/asignacion-competencias/', views.asignacion_competencias_view, name='asignacion_competencias'),

    # 🔒 RUTA PARA EL CAMBIO DE CONTRASEÑA OBLIGATORIO
    path('cambiar-password-obligatorio/', views.cambiar_password_obligatorio, name='cambiar_password_obligatorio'),

    # 🌟 REDIRECCIÓN: Si el usuario escribe /admin/ o /admin en la URL
    path('admin/', RedirectView.as_view(url='/admin/dashboard/', permanent=False)),

    path('admin/procesar-evaluaciones-loading/<str:session_key>/', admin_site.admin_view(procesar_evaluaciones_loading_view), name='procesar_evaluaciones_loading'),

    path('evaluacion/acceso/<uuid:token_uuid>/', views.acceso_magico_view, name='acceso_magico'),
    path('evaluacion/guardar/', views.guardar_evaluacion_view, name='guardar_evaluacion'),
    path('cerrar-sesion/', views.cerrar_sesion_view, name='cerrar_sesion'),

    # Se monta el sitio con un prefijo para incluir todas las rutas internas de los modelos
    #path('admin/site/', admin_site.urls),
    path('admin/', admin_site.urls),
]