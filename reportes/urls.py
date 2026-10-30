
from django.urls import path
from . import views  # 👈 ESTA LÍNEA ES LA QUE FALTABA

app_name = 'reportes'

urlpatterns = [
    path('pivot/<slug:slug>/', views.reporte_dinamico_view, name='reporte_dinamico'),
    path('tablas/', views.lista_tablas_dinamicas_view, name='lista_tablas'),
    path('api/guardar-plantilla/', views.guardar_plantilla_pivot, name='guardar_plantilla_pivot'),
    path('api/eliminar-plantilla/', views.eliminar_plantilla_pivot, name='eliminar_plantilla_pivot'),
    path('api/predeterminar-plantilla/', views.predeterminar_plantilla_pivot, name='predeterminar_plantilla_pivot'),
]