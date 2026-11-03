"""
Crea la plantilla de Excel (Power Query) de un reporte: reportes/plantillas_excel/<slug>.xlsx y <slug>.json.

    python manage.py crear_plantilla_excel inventario-fruverpack
    python manage.py crear_plantilla_excel ventas --empresa FRUSA

Se corre en una computadora con Windows y Excel instalado (usa scripts/crear_plantilla_excel.ps1, que maneja
Excel por COM). El servidor solo sirve el archivo ya creado: hay que subirlo al repositorio y hacer deploy.

- Columnas y tipos: se corre el query_sql del reporte (solo lectura) con la empresa y las fechas por omisión.
- Acomodo de la tabla dinámica: configuracion_pivot (área, orden, nombre visible, resumen, formato) y el
  filtro avanzado sencillo (contiene / no contiene / empieza / termina / igual / diferente unidos con "and").
- Cada vez que se crea cambia la versión; los Excel con una versión anterior ven un aviso en Parámetros.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from reportes.excel import CARPETA_PLANTILLAS, tipos_de_columnas
from reportes.models import Pivot_Dinamico
from reportes.views import ejecutar_consulta_reporte, resolver_macro_fecha

SCRIPT = Path(settings.BASE_DIR) / 'scripts' / 'crear_plantilla_excel.ps1'
HOJA_PARAMETROS = 'Parámetros'
CELDAS = {'servidor': 'C4', 'empresa': 'C5', 'empresas': 'D5', 'fecha_inicio': 'C6', 'fecha_fin': 'C7'}
NOMBRES = {'servidor': 'pServidor', 'empresa': 'pEmpresa', 'fecha_inicio': 'pFechaInicio', 'fecha_fin': 'pFechaFin'}

# XlConsolidationFunction y XlPivotFilterType de Excel
RESUMENES = {'sum': -4157, 'count': -4112, 'avg': -4106, 'min': -4139, 'max': -4136}
FILTROS = {'=': 15, '<>': 16, 'startswith': 17, 'endswith': 19, 'contains': 21, 'notcontains': 22}


def formato_excel(formato):
    """Formato de DevExtreme -> formato de número de Excel (igual que formatoExcel en pivot_generico.html)."""
    if isinstance(formato, dict):
        decimales = formato.get('precision', 2)
        ceros = '.' + '0' * decimales if decimales > 0 else ''
        return {'percent': '0' + ceros + '%', 'currency': '"$"#,##0' + ceros, 'fixedPoint': '#,##0' + ceros}.get(formato.get('type'))
    if formato == 'percent':
        return '0.00%'
    if formato == 'currency':
        return '"$"#,##0.00'
    if isinstance(formato, str) and any(c in formato for c in '#0'):
        return formato.replace('$', '"$"')
    return None


def texto_m(valor):
    return '"' + str(valor).replace('"', '""') + '"'


def lista_m(valores):
    return '{' + ', '.join(texto_m(v) for v in valores) + '}'


ENCABEZADO_M = '''let
    Celda = (nombre) => Excel.CurrentWorkbook(){[Name = nombre]}[Content]{0}[Column1],
    Texto = (valor) => if valor = null then "" else if valor is datetime or valor is date then Date.ToText(Date.From(valor), "yyyy-MM-dd") else Text.Trim(Text.From(valor)),
    Servidor = Text.TrimEnd(Texto(Celda("pServidor")), "/"),
    Parametros = [empresa = Texto(Celda("pEmpresa")), fecha_inicio = Texto(Celda("pFechaInicio")), fecha_fin = Texto(Celda("pFechaFin")), version = VERSION],
'''


def m_datos(slug, version, pares, esperadas):
    """Consulta Datos: llama a la API con los parámetros de la hoja; sin servidor regresa la tabla vacía."""
    return (ENCABEZADO_M.replace('VERSION', texto_m(version)) + '''    Pares = PARES,
    Esperadas = ESPERADAS,
    Titulo = (nombre) => let par = List.Select(Pares, each _{0} = nombre) in if List.IsEmpty(par) then nombre else par{0}{1},
    TipoM = (tipo) => if tipo = "numero" then type number else if tipo = "fecha" then type date else if tipo = "fechahora" then type datetime else if tipo = "logico" then type logical else if tipo = "texto" then type text else type any,
    Consultar = () =>
        let
            Respuesta = Web.Contents(Servidor, [RelativePath = "reportes/excel/api/SLUG/", Query = Parametros,
                ManualStatusHandling = {400, 403, 404, 500}, Timeout = #duration(0, 0, 10, 0)]),
            Estatus = Value.Metadata(Respuesta)[Response.Status],
            Json = try Json.Document(Respuesta) otherwise [mensaje = "El portal respondió con error " & Text.From(Estatus)],
            Validado = if Estatus = 200 then Json else error Error.Record("SITE FRUVER", Record.FieldOrDefault(Json, "mensaje", "Error " & Text.From(Estatus))),
            Columnas = List.Transform(Validado[columnas], each {Titulo([nombre]), [tipo]}),
            Nombres = List.Transform(Columnas, each _{0}),
            Tabla = Table.FromRows(Validado[datos], Nombres),
            Fechas = List.Transform(List.Select(Columnas, each _{1} = "fecha" or _{1} = "fechahora"),
                each {_{0}, if _{1} = "fecha" then (v) => if v = null then null else Date.FromText(v) else (v) => if v = null then null else DateTime.FromText(v)}),
            Convertida = Table.TransformColumns(Tabla, Fechas),
            Tipada = Table.TransformColumnTypes(Convertida, List.Transform(Columnas, each {_{0}, TipoM(_{1})})),
            Ordenada = Table.SelectColumns(Tipada, List.Distinct(Esperadas & Nombres), MissingField.UseNull)
        in
            Ordenada,
    Resultado = if Servidor = "" then #table(Esperadas, {}) else Consultar()
in
    Resultado''').replace('SLUG', slug).replace('PARES', '{' + ', '.join(lista_m(p) for p in pares) + '}') \
        .replace('ESPERADAS', lista_m(esperadas))


def m_estado(slug, version):
    """Consulta Estado: usuario conectado, empresa, hora y aviso (versión vieja, empresa sin acceso)."""
    return (ENCABEZADO_M.replace('VERSION', texto_m(version)) + '''    Encabezados = {"Usuario", "Empresa", "Consultado", "Aviso"},
    Consultar = () =>
        let
            J = Json.Document(Web.Contents(Servidor, [RelativePath = "reportes/excel/api/SLUG/estado/",
                Query = [empresa = Parametros[empresa], version = Parametros[version]]])),
            Empresa = if J[empresa] = "" then "" else J[empresa] & " - " & J[nombre_empresa]
        in
            #table(Encabezados, {{J[usuario], Empresa, J[consultado], J[aviso]}}),
    Resultado = if Servidor = "" then #table(Encabezados, {}) else Consultar()
in
    Resultado''').replace('SLUG', slug)


class Command(BaseCommand):
    help = "Crea la plantilla de Excel (Power Query) de un reporte. Requiere Windows con Excel."

    def add_arguments(self, parser):
        parser.add_argument('slug')
        parser.add_argument('--empresa', default='FRUSA', help="Empresa con la que se corre la consulta para conocer las columnas")
        parser.add_argument('--visible', action='store_true', help="Muestra Excel mientras se crea (para revisar)")

    def handle(self, slug, empresa, visible, **opciones):
        reporte = Pivot_Dinamico.objects.filter(slug=slug).first()
        if not reporte:
            raise CommandError(f'No existe el reporte {slug}')
        if not SCRIPT.exists():
            raise CommandError(f'No se encontró {SCRIPT}')

        fecha_inicio = resolver_macro_fecha(reporte.fecha_inicio_macro or '-3m')
        fecha_fin = resolver_macro_fecha(reporte.fecha_fin_macro or 'm')
        columnas, filas = ejecutar_consulta_reporte(reporte, empresa, fecha_inicio, fecha_fin)
        tipos = dict(zip(columnas, tipos_de_columnas(columnas, filas)))
        self.stdout.write(f'Columnas ({len(filas)} filas de muestra): ' + ', '.join(f'{c} [{tipos[c]}]' for c in columnas))

        config = reporte.configuracion_pivot or []
        campos = config.get('fields', []) if isinstance(config, dict) else config
        opciones_pivot = config if isinstance(config, dict) else {}

        # Nombre visible de cada columna (caption). Los campos calculados de la página (sin columna) no aplican.
        titulos = {}
        for campo in campos:
            columna = campo.get('dataField')
            if columna in tipos and columna not in titulos and campo.get('caption'):
                titulos[columna] = campo['caption']
        esperadas, usados = [], set()
        for columna in columnas:
            titulo = titulos.get(columna, columna)
            if titulo in usados:  # dos columnas con el mismo caption: la segunda conserva su nombre
                titulo = columna
            usados.add(titulo)
            titulos[columna] = titulo
            esperadas.append(titulo)

        areas = {'row': [], 'column': [], 'filter': [], 'data': []}
        for campo in campos:
            columna, area = campo.get('dataField'), campo.get('area')
            if columna not in tipos or area not in areas or campo.get('visible') is False:
                if area in areas and columna not in tipos:
                    self.stdout.write(self.style.WARNING(f'  Se omite "{campo.get("caption") or columna}": no es una columna de la consulta'))
                continue
            areas[area].append((campo.get('areaIndex', 999), campo))
        acomodo = {area: [c for _, c in sorted(lista, key=lambda x: x[0])] for area, lista in areas.items()}

        datos = []
        for campo in acomodo['data']:
            resumen = campo.get('summaryType', 'sum')
            if resumen not in RESUMENES:
                self.stdout.write(self.style.WARNING(f'  Resumen "{resumen}" de {campo["dataField"]} no existe en Excel: se usa suma'))
            datos.append({'campo': titulos[campo['dataField']], 'titulo': campo.get('caption') or campo['dataField'],
                          'resumen': RESUMENES.get(resumen, RESUMENES['sum']),
                          'formato': formato_excel(campo.get('format')) or ('#,##0.00' if tipos[campo['dataField']] == 'numero' else '#,##0')})

        filtros = []
        avanzado = opciones_pivot.get('filtroAvanzado') or {}
        if avanzado.get('activo') and avanzado.get('valor'):
            filtros = self._filtros_de_etiqueta(avanzado['valor'], titulos)

        version = timezone.localtime().strftime('%Y%m%d%H%M')
        spec = {
            'nombre': reporte.nombre,
            'hoja_parametros': HOJA_PARAMETROS,
            'celdas': CELDAS,
            'nombres': NOMBRES,
            'version': version,
            'm_datos': m_datos(slug, version, [[c, titulos[c]] for c in columnas if titulos[c] != c], esperadas),
            'm_estado': m_estado(slug, version),
            'filas': [titulos[c['dataField']] for c in acomodo['row']],
            'columnas': [titulos[c['dataField']] for c in acomodo['column']],
            'filtros_pagina': [titulos[c['dataField']] for c in acomodo['filter']],
            'datos': datos,
            'filtros_etiqueta': filtros,
            'subtotales': opciones_pivot.get('showRowTotals', True) is not False,
            'visible': visible,
        }

        CARPETA_PLANTILLAS.mkdir(parents=True, exist_ok=True)
        salida = CARPETA_PLANTILLAS / f'{slug}.xlsx'
        with tempfile.TemporaryDirectory() as carpeta:
            archivo_spec = Path(carpeta) / 'spec.json'
            archivo_spec.write_text(json.dumps(spec, ensure_ascii=False), encoding='utf-8')
            temporal = Path(carpeta) / f'{slug}.xlsx'
            resultado = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT),
                 '-Spec', str(archivo_spec), '-Salida', str(temporal)],
                capture_output=True, text=True, encoding='utf-8', errors='replace')
            if resultado.stdout.strip():
                self.stdout.write(resultado.stdout.strip())
            if resultado.returncode != 0 or not temporal.exists():
                raise CommandError('Excel no pudo crear la plantilla:\n' + (resultado.stderr or resultado.stdout))
            salida.write_bytes(temporal.read_bytes())

        info = {'version': version, 'hoja_parametros': HOJA_PARAMETROS, 'celdas': CELDAS,
                'columnas': esperadas, 'creada': timezone.localtime().isoformat(timespec='seconds')}
        (CARPETA_PLANTILLAS / f'{slug}.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Plantilla creada: {salida} (versión {version})'))

    def _filtros_de_etiqueta(self, valor, titulos):
        """[["Etiqueta","notcontains","DESECHO"], "and", [...]] -> filtros de etiqueta de Excel (uno por campo)."""
        condiciones = valor if valor and isinstance(valor[0], list) else [valor]
        if any(isinstance(c, str) and c.lower() != 'and' for c in condiciones):
            self.stdout.write(self.style.WARNING('  El filtro avanzado usa "or": no se pasa a Excel'))
            return []
        filtros, campos = [], set()
        for condicion in condiciones:
            if not isinstance(condicion, list):
                continue
            if len(condicion) != 3 or condicion[1] not in FILTROS or condicion[0] not in titulos or condicion[0] in campos:
                self.stdout.write(self.style.WARNING(f'  Filtro {condicion} no se puede pasar a Excel: se omite'))
                continue
            campos.add(condicion[0])
            filtros.append({'campo': titulos[condicion[0]], 'tipo': FILTROS[condicion[1]], 'valor': str(condicion[2])})
        return filtros
