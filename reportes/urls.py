# reportes/urls.py
from django.urls import path
from .views import reporte_dinamico_view, lista_tablas_dinamicas_view

app_name = 'reportes'

urlpatterns = [
    path('reportes/pivot/', lista_tablas_dinamicas_view, name='lista_tablas_dinamicas'),
    path('reportes/pivot/<slug:slug>/', reporte_dinamico_view, name='reporte_pivot_dinamico'),
]