"""
Tablero de maquila: los datos del reporte "Proceso de maquila" (rep_proceso_maquila) en forma de tablero.

- Por productor: dueños a la izquierda, sus procesos (estibas) con los datos principales y la ficha del
  proceso como la que se le manda al productor (copiar para WhatsApp, imagen, imprimir) o la ficha
  concentrada de todos sus procesos.
- General: indicadores, productores que más maquilaron, variedades, presentaciones, tamaños y tendencia.

Usa el mismo permiso que la tabla dinámica (permiso_codename del reporte proceso-maquila).
"""
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from core_app.empresas import logo_de_empresa
from rh.models import Empresa
from .models import Pivot_Dinamico
from .views import ejecutar_consulta_reporte, resolver_macro_fecha, usuario_puede_ver_reporte

SLUG_REPORTE = 'proceso-maquila'


def _reporte_permitido(request):
    reporte = get_object_or_404(Pivot_Dinamico, slug=SLUG_REPORTE, activo=True)
    if not usuario_puede_ver_reporte(request.user, reporte):
        raise PermissionDenied
    return reporte


@login_required
def tablero_maquila_view(request):
    reporte = _reporte_permitido(request)
    empresa = Empresa.objects.filter(pk=getattr(request.user, '_empresa_activa', None)).first()
    return render(request, 'reportes/tablero_maquila.html', {
        'nombre_empresa': empresa.nombre if empresa else '',
        'logo_empresa_url': (empresa and logo_de_empresa(empresa)) or '',
        'fecha_inicio': resolver_macro_fecha(reporte.fecha_inicio_macro or '-1m').isoformat(),
        'fecha_fin': resolver_macro_fecha(reporte.fecha_fin_macro or 'm').isoformat(),
    })


def _fecha_get(request, nombre, macro):
    valor = request.GET.get(nombre, '')
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except ValueError:
        return resolver_macro_fecha(macro)


@login_required
@require_GET
def datos_maquila_view(request):
    """Renglones del reporte en el periodo: {"columnas": [...], "filas": [[...], ...]} (arreglos, pesa menos)."""
    reporte = _reporte_permitido(request)
    fecha_inicio = _fecha_get(request, 'fecha_inicio', reporte.fecha_inicio_macro or '-1m')
    fecha_fin = _fecha_get(request, 'fecha_fin', reporte.fecha_fin_macro or 'm')
    empresa = getattr(request.user, '_empresa_activa', None)
    columnas, filas = ejecutar_consulta_reporte(reporte, empresa, fecha_inicio, fecha_fin)

    def valor(v):
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (date, datetime)):
            return v.isoformat()[:10]
        return v

    return JsonResponse({
        'fecha_inicio': fecha_inicio.isoformat(),
        'fecha_fin': fecha_fin.isoformat(),
        'columnas': columnas,
        'filas': [[valor(v) for v in fila] for fila in filas],
    })
