from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'vacaciones'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='vacaciones:mis_vacaciones', permanent=False)),
    path('mis/', views.mis_vacaciones_view, name='mis_vacaciones'),
    path('solicitar/', views.solicitar_view, name='solicitar'),
    path('calcular/', views.calcular_view, name='calcular'),
    path('aprobaciones/', views.aprobaciones_view, name='aprobaciones'),
    path('solicitud/<int:pk>/accion/', views.accion_view, name='accion'),
    path('formato/<int:pk>/', views.formato_view, name='formato'),
    path('personal/', views.personal_view, name='personal'),
    path('personal/<int:empleado_pk>/', views.mis_vacaciones_view, name='empleado'),
    path('solicitudes/', views.solicitudes_view, name='solicitudes'),
]
