import json
from decimal import Decimal
from datetime import date, datetime
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import connection
from .models import Pivot_Dinamico

@login_required
def reporte_dinamico_view(request, slug):
    reporte = get_object_or_404(Pivot_Dinamico, slug=slug, activo=True)
    empresa_activa = request.session.get('empresa_activa') or request.session.get('empresa_id')

    datos = []
    with connection.cursor() as cursor:
        if "%s" in reporte.query_sql and empresa_activa:
            cursor.execute(reporte.query_sql, [empresa_activa])
        else:
            cursor.execute(reporte.query_sql)
        
        columnas = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        
        for row in rows:
            fila_dict = {}
            for col, val in zip(columnas, row):
                # Convertir Decimal a float y fechas a cadena ISO para ser compatibles con JSON
                if isinstance(val, Decimal):
                    val = float(val)
                elif isinstance(val, (date, datetime)):
                    val = val.isoformat()
                fila_dict[col] = val
            datos.append(fila_dict)

    context = {
        'titulo_reporte': reporte.nombre,
        'datos_json': datos,
        'configuracion_pivot': reporte.configuracion_pivot or [],
    }
    return render(request, 'reportes/pivot_generico.html', context)

@login_required
def lista_tablas_dinamicas_view(request):
    # Consulta todos los reportes activos ordenados por el campo 'orden' o 'nombre'
    reportes = Pivot_Dinamico.objects.filter(activo=True).order_by('orden', 'nombre')
    
    return render(request, "reportes/lista_tablas.html", {
        "reportes": reportes
    })