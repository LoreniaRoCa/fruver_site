import os
import json
from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.contrib import admin
from .models import Pivot_Dinamico, PlantillaPivotUsuario
from rh.models import Empresa  # 🟢 IMPORTACIÓN DEL MODELO EMPRESA
from django.conf import settings  # 🟢 AGREGADO
from django.templatetags.static import static  # 🟢 AGREGADO

def resolver_macro_fecha(token):
    """Convierte tokens como '-3m', 'm', 'A1', 'a' a objetos date de Python."""
    if not token:
        return date.today()
    
    token = str(token).strip()
    hoy = date.today()

    if token == "A1":
        return date(hoy.year, 1, 1)
    if token == "a":
        return date(hoy.year, 12, 31)
    if token == "-1a":
        return date(hoy.year - 1, 1, 1)
    if token == "M":

        return date(hoy.year, hoy.month, 1)
    if token == "m":
        # Último día del mes actual
        siguiente_mes = hoy + relativedelta(months=1)
        return date(siguiente_mes.year, siguiente_mes.month, 1) - relativedelta(days=1)
    if token in ["Hoy", "D"]:
        return hoy

    # Evaluación de patrones -Nm / +Nm (ej: -3m)
    if token.endswith('m') or token.endswith('M'):
        try:
            num_meses = int(token[:-1])
            base = hoy + relativedelta(months=num_meses)
            return date(base.year, base.month, 1)
        except ValueError:
            pass

    # Evaluación de patrones -Nd / +Nd (ej: -7d)
    if token.endswith('d') or token.endswith('D'):
        try:
            num_dias = int(token[:-1])
            return hoy + relativedelta(days=num_dias)
        except ValueError:
            pass

    # Si viene como fecha ISO 'YYYY-MM-DD'
    try:
        return datetime.strptime(token, "%Y-%m-%d").date()
    except ValueError:
        return hoy

def usuario_puede_ver_reporte(user, reporte):
    """Valida permiso_codename del reporte (ej. 'ver_ventas_pivot' o 'reportes.ver_ventas_pivot')."""
    codename = (reporte.permiso_codename or "").strip()
    if not codename:
        return True
    if "." not in codename:
        codename = f"reportes.{codename}"
    return user.has_perm(codename)

# reportes/views.py

@login_required
def reporte_dinamico_view(request, slug):
    reporte = get_object_or_404(Pivot_Dinamico, slug=slug, activo=True)
    if not usuario_puede_ver_reporte(request.user, reporte):
        raise PermissionDenied
    # 🟢 Unificar el nombre de la variable
    empresa_activa_id = request.session.get('empresa_activa') or request.session.get('empresa_id')

    # Fallbacks por defecto usando static()
    logo_empresa_url = static("img/logo.png")
    nombre_empresa = "EMPRESA"

    if empresa_activa_id:
        empresa = Empresa.objects.filter(pk=empresa_activa_id).first()
        if empresa:
            nombre_empresa = empresa.nombre
            
            if hasattr(empresa, 'logo') and empresa.logo:
                logo_empresa_url = empresa.logo.url
            else:
                # Mapeo a static/img/logo_<id_empresa>.png
                empresa_id_str = str(empresa_activa_id).strip().lower()
                rel_path = f"img/logo_{empresa_id_str}.png"
                full_path = os.path.join(settings.BASE_DIR, 'static', rel_path)
                
                if os.path.exists(full_path):
                    logo_empresa_url = static(rel_path)
                else:
                    logo_empresa_url = static("img/logo.png")

    # Captura de parámetros desde GET
    fecha_inicio_raw = request.GET.get('fecha_inicio')
    fecha_fin_raw = request.GET.get('fecha_fin')

    if fecha_inicio_raw:
        fecha_inicio_val = resolver_macro_fecha(fecha_inicio_raw)
    else:
        fecha_inicio_val = resolver_macro_fecha(reporte.fecha_inicio_macro or "-3m")

    if fecha_fin_raw:
        fecha_fin_val = resolver_macro_fecha(fecha_fin_raw)
    else:
        fecha_fin_val = resolver_macro_fecha(reporte.fecha_fin_macro or "m")

    datos = []
    with connection.cursor() as cursor:
        num_params = reporte.query_sql.count("%s")
        params = []

        if num_params == 3:
            params = [empresa_activa_id, fecha_inicio_val, fecha_fin_val]
        elif num_params == 2:
            params = [fecha_inicio_val, fecha_fin_val]
        elif num_params == 1:
            params = [empresa_activa_id]

        if params:
            cursor.execute(reporte.query_sql, params)
        else:
            cursor.execute(reporte.query_sql)
        
        columnas = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        
        for row in rows:
            fila_dict = {}
            for col, val in zip(columnas, row):
                if isinstance(val, Decimal):
                    val = float(val)
                elif isinstance(val, (date, datetime)):
                    val = val.isoformat()
                fila_dict[col] = val
            datos.append(fila_dict)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse({
                'status': 'success',
                'datos': datos,
                'fecha_inicio': fecha_inicio_val.isoformat(),
                'fecha_fin': fecha_fin_val.isoformat(),
                'nombre_empresa': nombre_empresa,
                'logo_empresa_url': logo_empresa_url
            })
    plantillas_qs = PlantillaPivotUsuario.objects.filter(
        reporte_base_id=reporte.id_reporte,
        usuario=request.user
    ).values('id', 'nombre_plantilla', 'configuracion_pivot', 'fecha_inicio_macro', 'fecha_fin_macro', 'es_default')

    plantillas_usuario_list = []
    for item in plantillas_qs:
        item['fecha_inicio_macro'] = item['fecha_inicio_macro'] or reporte.fecha_inicio_macro
        item['fecha_fin_macro'] = item['fecha_fin_macro'] or reporte.fecha_fin_macro
        plantillas_usuario_list.append(item)

    lista_plantillas = [
        {
            'id': 0,
            'nombre_plantilla': f'*** {reporte.nombre.upper()} (DEFAULT) ***',
            'configuracion_pivot': reporte.configuracion_pivot,
            'fecha_inicio_macro': reporte.fecha_inicio_macro,
            'fecha_fin_macro': reporte.fecha_fin_macro,
            'es_default': True
        }
    ] + plantillas_usuario_list

    context = admin.site.each_context(request)
    context.update({
        'titulo_reporte': reporte.nombre,
        'nombre_empresa': nombre_empresa,
        'logo_empresa_url': logo_empresa_url,  # 👈 Pasamos el logo al contexto
        'datos_json': datos,
        'configuracion_pivot': reporte.configuracion_pivot or [],
        'plantillas_usuario': lista_plantillas,
        'reporte_id': reporte.id_reporte,
        'fecha_inicio_actual': fecha_inicio_val.isoformat(),
        'fecha_fin_actual': fecha_fin_val.isoformat(),
    })
    
    return render(request, 'reportes/pivot_generico.html', context)


@login_required
def lista_tablas_dinamicas_view(request):
    reportes = [
        r for r in Pivot_Dinamico.objects.filter(activo=True).order_by('orden', 'nombre')
        if usuario_puede_ver_reporte(request.user, r)
    ]

    context = admin.site.each_context(request)
    context.update({
        "reportes": reportes
    })
    
    return render(request, "reportes/lista_tablas.html", context)


@login_required
@require_POST
def guardar_plantilla_pivot(request):
    try:
        data = json.loads(request.body)
        reporte_id = data.get('reporte_id')
        nombre = data.get('nombre_plantilla')
        config_json = data.get('configuracion_pivot')
        fecha_inicio_macro = data.get('fecha_inicio_macro', '-3m')
        fecha_fin_macro = data.get('fecha_fin_macro', 'm')
        
        if not reporte_id or not nombre or not config_json:
            return JsonResponse({'status': 'error', 'message': 'Faltan datos requeridos'}, status=400)

        reporte = Pivot_Dinamico.objects.filter(pk=reporte_id, activo=True).first()
        if not reporte or not usuario_puede_ver_reporte(request.user, reporte):
            return JsonResponse({'status': 'error', 'message': 'No tiene permiso sobre este reporte'}, status=403)

        plantilla, created = PlantillaPivotUsuario.objects.update_or_create(
            reporte_base_id=reporte_id,
            usuario=request.user,
            nombre_plantilla=nombre,
            defaults={
                'configuracion_pivot': config_json,
                'fecha_inicio_macro': fecha_inicio_macro,
                'fecha_fin_macro': fecha_fin_macro,
            }
        )

        return JsonResponse({
            'status': 'success',
            'id': plantilla.id,
            'created': created,
            'message': 'Plantilla guardada correctamente'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)