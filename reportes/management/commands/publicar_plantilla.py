"""
Convierte una plantilla de usuario en el formato base de su reporte SIN perder las definiciones
de los campos (caption, format, dataType, cocientes...).

    python manage.py publicar_plantilla 5 --simular     (muestra qué cambiaría)
    python manage.py publicar_plantilla 5               (lo guarda; deja respaldo en Respaldos/)

La plantilla solo guarda el acomodo (state() de DevExtreme: área, orden, filtros...), así que se
toma de ella ese acomodo y se aplica sobre los campos del formato base, igual que hace la página
al abrir una plantilla. También se copia el filtro avanzado.
"""
import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reportes.models import PlantillaPivotUsuario

# Las mismas propiedades que la página toma de una plantilla (PROPIEDADES_ACOMODO en pivot_generico.html)
PROPIEDADES_ACOMODO = ["area", "areaIndex", "sortOrder", "sortBy", "sortBySummaryField", "sortBySummaryPath",
                       "expanded", "filterValues", "filterType", "summaryType", "summaryDisplayMode", "width"]


def clave_campo(campo):
    """
    name si el campo lo tiene (dos campos pueden compartir dataField, p. ej. "Venta Neta" y "% Venta"
    sobre VentaNeta) y si no dataField. Los cocientes sin name usan el que les pone la página.
    Igual que camposConAcomodo en pivot_generico.html.
    """
    if campo.get('name'):
        return campo['name']
    if campo.get('cociente'):
        c = campo['cociente']
        return f"cociente_{c.get('numerador')}_{c.get('denominador')}"
    return campo.get('dataField') or campo.get('FieldName')


def describir(campo):
    area = campo.get('area') or '(Todos los campos)'
    orden = f" #{campo['areaIndex']}" if campo.get('areaIndex') is not None and campo.get('area') else ''
    return f"{area}{orden}"


class Command(BaseCommand):
    help = "Publica una plantilla de usuario como formato base de su reporte, conservando las definiciones de los campos."

    def add_arguments(self, parser):
        parser.add_argument('plantilla_id', type=int, help="id en rep_plantilla_pivot_usuario")
        parser.add_argument('--simular', action='store_true', help="Muestra los cambios sin guardar")

    def handle(self, *args, **opciones):
        plantilla = PlantillaPivotUsuario.objects.select_related('reporte_base').filter(pk=opciones['plantilla_id']).first()
        if not plantilla:
            raise CommandError(f"No existe la plantilla {opciones['plantilla_id']}")
        reporte = plantilla.reporte_base

        base = reporte.configuracion_pivot or []
        if isinstance(base, str):
            base = json.loads(base)
        campos_base = base if isinstance(base, list) else (base.get('fields') or base.get('Fields') or [])
        if not campos_base:
            raise CommandError(f"El formato base de '{reporte.nombre}' no tiene campos")

        estado = plantilla.configuracion_pivot
        if isinstance(estado, str):
            estado = json.loads(estado)
        acomodo = {}
        for c in estado.get('fields') or []:
            clave = clave_campo(c)
            if clave and clave not in acomodo:
                acomodo[clave] = c

        nuevos, cambios = [], []
        for campo in campos_base:
            nuevo = dict(campo)
            guardado = acomodo.get(clave_campo(campo))
            # El lugar lo decide la plantilla; el resto de la definición se queda como en el formato base
            nuevo.pop('area', None)
            nuevo.pop('areaIndex', None)
            for p in PROPIEDADES_ACOMODO:
                if guardado and guardado.get(p) is not None:
                    nuevo[p] = guardado[p]
            if not nuevo.get('area'):
                # Sin área en la plantilla = en "Todos los campos" (Selector de Campos)
                nuevo.pop('area', None)
                nuevo.pop('areaIndex', None)
            if describir(campo) != describir(nuevo):
                cambios.append(f"  {nuevo.get('caption') or clave_campo(campo)}: {describir(campo)} -> {describir(nuevo)}")
            nuevos.append(nuevo)

        filtro = estado.get('filtroAvanzado')
        resultado = {'fields': nuevos, 'filtroAvanzado': filtro} if filtro else nuevos

        self.stdout.write(f"Plantilla '{plantilla.nombre_plantilla}' ({plantilla.usuario}) -> formato base de '{reporte.nombre}' (id {reporte.pk})")
        self.stdout.write(f"{len(nuevos)} campos; definiciones (caption, format, cocientes) conservadas del formato base.")
        self.stdout.write(f"Campos que cambian de lugar: {len(cambios)}")
        for linea in cambios:
            self.stdout.write(linea)
        self.stdout.write(f"Filtro avanzado: {json.dumps(filtro, ensure_ascii=False) if filtro else 'ninguno'}")

        if opciones['simular']:
            self.stdout.write(self.style.NOTICE("Simulación: no se guardó nada."))
            return

        carpeta = Path(settings.BASE_DIR) / 'Respaldos'
        carpeta.mkdir(exist_ok=True)
        respaldo = carpeta / f"formato_base_{reporte.slug}_{datetime.now():%Y%m%d_%H%M%S}.json"
        respaldo.write_text(json.dumps(reporte.configuracion_pivot, ensure_ascii=False, indent=1), encoding='utf-8')

        reporte.configuracion_pivot = resultado
        reporte.save(update_fields=['configuracion_pivot'])
        self.stdout.write(self.style.SUCCESS(f"Formato base actualizado. Respaldo del anterior: {respaldo}"))
