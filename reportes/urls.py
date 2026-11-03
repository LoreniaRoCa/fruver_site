
from django.urls import path
from . import excel, views  # 👈 ESTA LÍNEA ES LA QUE FALTABA

app_name = 'reportes'

urlpatterns = [
    path('pivot/<slug:slug>/', views.reporte_dinamico_view, name='reporte_dinamico'),
    path('tablas/', views.lista_tablas_dinamicas_view, name='lista_tablas'),
    path('api/guardar-plantilla/', views.guardar_plantilla_pivot, name='guardar_plantilla_pivot'),
    path('api/eliminar-plantilla/', views.eliminar_plantilla_pivot, name='eliminar_plantilla_pivot'),
    path('api/predeterminar-plantilla/', views.predeterminar_plantilla_pivot, name='predeterminar_plantilla_pivot'),
    # Reportes en Excel (Power Query)
    path('excel/', excel.inicio_excel_view, name='excel_inicio'),
    path('excel/claves/nueva/', excel.nueva_clave_excel_view, name='excel_nueva_clave'),
    path('excel/claves/<int:pk>/revocar/', excel.revocar_clave_excel_view, name='excel_revocar_clave'),
    path('excel/<slug:slug>/plantilla/', excel.descargar_plantilla_excel_view, name='excel_plantilla'),
    path('excel/api/<slug:slug>/', excel.api_datos, name='excel_api_datos'),
    path('excel/api/<slug:slug>/estado/', excel.api_estado, name='excel_api_estado'),
]