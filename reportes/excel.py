"""
Reportes en Excel (Power Query).

El usuario descarga del portal la plantilla de un reporte (reportes/plantillas_excel/<slug>.xlsx, creada con
`manage.py crear_plantilla_excel`), escribe empresa y fechas en la hoja Parámetros y en Excel usa
Datos > Actualizar todo. Power Query llama a:

- api/<slug>/          los datos del reporte (mismo query_sql y permisos que la tabla dinámica del portal)
- api/<slug>/estado/   quién está conectado, empresa y aviso si hay una versión más nueva de la plantilla

Autenticación "Básica" de Excel: usuario del portal + su clave de Excel (ClaveExcel), nunca su contraseña.
Cada consulta de datos queda en BitacoraConsultaExcel.
"""
import base64
import hashlib
import io
import json
import re
import secrets
import time
import zipfile
from datetime import date, datetime, time as hora
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_GET, require_POST

from core_app.empresas import empresas_permitidas
from .models import BitacoraConsultaExcel, ClaveExcel, Pivot_Dinamico
from .views import ejecutar_consulta_reporte, resolver_macro_fecha, usuario_puede_ver_reporte

CARPETA_PLANTILLAS = Path(settings.BASE_DIR) / 'reportes' / 'plantillas_excel'
MAX_FILAS = 500_000
REINO = 'SITE FRUVER - Excel'
PATRON_FECHA = re.compile(r'^(\d{4}-\d{2}-\d{2}|A1|a|-1a|M|m|Hoy|D|[+-]?\d+[mMdD])$')
ENTERO_SIN_CEROS = re.compile(r'^[1-9]\d{0,14}$')
CON_CERO_INICIAL = re.compile(r'^0\d+$')


# ---------------------------------------------------------------- claves

def _hash(clave):
    return hashlib.sha256(clave.encode('utf-8')).hexdigest()


def generar_clave(usuario, nombre):
    """Crea una clave nueva y regresa (ClaveExcel, clave en texto). El texto no se guarda: solo se muestra una vez."""
    clave = 'fx-' + secrets.token_urlsafe(30)
    obj = ClaveExcel.objects.create(usuario=usuario, nombre=nombre.strip()[:100] or 'Excel',
                                    prefijo=clave[:10], clave_hash=_hash(clave))
    return obj, clave


def _autenticar(request):
    """(usuario, clave, motivo). Sin encabezado Authorization: (None, None, None) para que Excel pida credenciales."""
    encabezado = request.META.get('HTTP_AUTHORIZATION', '')
    if not encabezado.lower().startswith('basic '):
        return None, None, None
    try:
        usuario_txt, _, clave_txt = base64.b64decode(encabezado[6:].strip()).decode('utf-8').partition(':')
    except (ValueError, UnicodeDecodeError):
        return None, None, 'Encabezado de autenticación inválido'

    usuario = get_user_model().objects.filter(username__iexact=usuario_txt.strip(), is_active=True).first()
    clave = None
    if usuario and clave_txt:
        clave = ClaveExcel.objects.filter(usuario=usuario, clave_hash=_hash(clave_txt.strip()), activa=True).first()
    if not clave:
        return usuario, None, 'Usuario o clave de Excel incorrectos'
    if clave.vence and clave.vence < timezone.localdate():
        return usuario, None, 'La clave de Excel venció; genera una nueva en el portal'

    ClaveExcel.objects.filter(pk=clave.pk).update(ultimo_uso=timezone.now())
    return usuario, clave, None


def _pedir_credenciales(mensaje):
    respuesta = JsonResponse({'estatus': 'error', 'mensaje': mensaje}, status=401)
    respuesta['WWW-Authenticate'] = f'Basic realm="{REINO}", charset="UTF-8"'
    return respuesta


def _ip(request):
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (reenviada.split(',')[0].strip() or request.META.get('REMOTE_ADDR')) or None


# ---------------------------------------------------------------- datos

def _empresa_de_la_consulta(usuario, empresa_txt):
    """(empresa, mensaje de error). Si no la escribió y solo tiene una empresa, se toma esa."""
    permitidas = list(empresas_permitidas(usuario))
    empresa_txt = (empresa_txt or '').strip().upper()
    if not empresa_txt:
        if len(permitidas) == 1:
            return permitidas[0], None
        return None, 'Escribe la empresa en la hoja Parámetros. Tus empresas: ' + ', '.join(e.pk for e in permitidas)
    for empresa in permitidas:
        if str(empresa.pk).upper() == empresa_txt:
            return empresa, None
    return None, f'No tienes acceso a la empresa {empresa_txt}. Tus empresas: ' + ', '.join(e.pk for e in permitidas)


def _fecha(valor, macro):
    valor = (valor or '').strip()
    if valor and not PATRON_FECHA.match(valor):
        raise ValueError(f'Fecha inválida: "{valor}". Usa una fecha de Excel o el formato AAAA-MM-DD')
    return resolver_macro_fecha(valor or macro)


def tipos_de_columnas(columnas, filas):
    """Tipo de cada columna para Power Query: numero, fecha, fechahora, logico, texto o mixto.
    "mixto" = texto con valores que son enteros (Tamaño: 56, 64 ... 216, CANICA): esos se mandan como número
    para que la tabla dinámica de Excel los ordene como en el portal (primero los números, luego el texto)."""
    tipos = []
    for i, _ in enumerate(columnas):
        valores = [f[i] for f in filas if f[i] is not None]
        primero = valores[0] if valores else None
        if isinstance(primero, bool):
            tipo = 'logico'
        elif isinstance(primero, (int, float, Decimal)):
            tipo = 'numero'
        elif isinstance(primero, datetime):
            tipo = 'fechahora'
        elif isinstance(primero, date):
            tipo = 'fecha'
        else:
            tipo = 'texto'
            textos = [v for v in valores if isinstance(v, str)]
            if any(ENTERO_SIN_CEROS.match(v) for v in textos) and not any(CON_CERO_INICIAL.match(v) for v in textos):
                tipo = 'mixto'
        tipos.append(tipo)
    return tipos


def _valor_json(valor, tipo):
    if valor is None or isinstance(valor, (bool, int, float)):
        return valor
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, datetime):
        return timezone.localtime(valor).replace(tzinfo=None).isoformat() if timezone.is_aware(valor) else valor.isoformat()
    if isinstance(valor, (date, hora)):
        return valor.isoformat()
    if tipo == 'mixto' and isinstance(valor, str) and ENTERO_SIN_CEROS.match(valor):
        return int(valor)
    return str(valor)


def _reporte_activo(slug):
    return Pivot_Dinamico.objects.filter(slug=slug, activo=True).first()


@require_GET
def api_datos(request, slug):
    inicio = time.monotonic()
    usuario, clave, motivo = _autenticar(request)
    reporte = _reporte_activo(slug)
    parametros = {k: request.GET.get(k, '') for k in ('empresa', 'fecha_inicio', 'fecha_fin')}
    version = request.GET.get('version', '')[:20]

    def responder(estatus_http, estatus, mensaje, empresa='', filas=0, cuerpo=None):
        BitacoraConsultaExcel.objects.create(
            usuario=usuario, clave=clave, reporte=reporte, empresa=empresa, parametros=parametros,
            version_plantilla=version, filas=filas, estatus=estatus, mensaje=mensaje[:2000], ip=_ip(request),
            duracion_ms=int((time.monotonic() - inicio) * 1000))
        if estatus_http == 401:
            return _pedir_credenciales(mensaje)
        return JsonResponse(cuerpo or {'estatus': 'error', 'mensaje': mensaje}, status=estatus_http)

    if not clave:
        if motivo is None:
            return _pedir_credenciales('Se requiere usuario y clave de Excel')  # primer intento de Excel, sin bitácora
        return responder(401, BitacoraConsultaExcel.DENEGADO, motivo)
    if not reporte:
        return responder(404, BitacoraConsultaExcel.ERROR, f'No existe el reporte "{slug}" o está inactivo')

    empresa, error = _empresa_de_la_consulta(usuario, parametros['empresa'])
    if error:
        return responder(403, BitacoraConsultaExcel.DENEGADO, error)
    usuario._empresa_activa = empresa.pk  # permisos de esa empresa (PermisosPorEmpresaBackend)
    if not usuario_puede_ver_reporte(usuario, reporte):
        return responder(403, BitacoraConsultaExcel.DENEGADO, f'No tienes permiso para el reporte {reporte.nombre} en {empresa.pk}', empresa.pk)

    try:
        fecha_inicio = _fecha(parametros['fecha_inicio'], reporte.fecha_inicio_macro or '-3m')
        fecha_fin = _fecha(parametros['fecha_fin'], reporte.fecha_fin_macro or 'm')
    except ValueError as e:
        return responder(400, BitacoraConsultaExcel.ERROR, str(e), empresa.pk)
    if fecha_inicio > fecha_fin:
        return responder(400, BitacoraConsultaExcel.ERROR, 'La fecha inicial es mayor que la final', empresa.pk)

    try:
        columnas, filas = ejecutar_consulta_reporte(reporte, empresa.pk, fecha_inicio, fecha_fin)
    except Exception as e:  # el detalle queda en la bitácora; a Excel solo un mensaje general
        BitacoraConsultaExcel.objects.create(
            usuario=usuario, clave=clave, reporte=reporte, empresa=empresa.pk, parametros=parametros,
            version_plantilla=version, estatus=BitacoraConsultaExcel.ERROR, mensaje=str(e)[:2000], ip=_ip(request),
            duracion_ms=int((time.monotonic() - inicio) * 1000))
        return JsonResponse({'estatus': 'error', 'mensaje': 'Error al consultar el reporte; avisa a sistemas'}, status=500)
    if len(filas) > MAX_FILAS:
        return responder(400, BitacoraConsultaExcel.ERROR,
                         f'La consulta regresa {len(filas):,} filas (máximo {MAX_FILAS:,}); reduce el periodo', empresa.pk, len(filas))

    tipos = tipos_de_columnas(columnas, filas)
    cuerpo = {
        'estatus': 'correcto',
        'reporte': reporte.slug,
        'empresa': empresa.pk,
        'fecha_inicio': fecha_inicio.isoformat(),
        'fecha_fin': fecha_fin.isoformat(),
        'columnas': [{'nombre': c, 'tipo': t} for c, t in zip(columnas, tipos)],
        'datos': [[_valor_json(v, t) for v, t in zip(fila, tipos)] for fila in filas],
    }
    return responder(200, BitacoraConsultaExcel.CORRECTO, '', empresa.pk, len(filas), cuerpo)


@require_GET
def api_estado(request, slug):
    """Renglón de estado de la hoja Parámetros. Siempre responde 200 (salvo credenciales) para mostrar el aviso."""
    usuario, clave, motivo = _autenticar(request)
    if not clave:
        return _pedir_credenciales(motivo or 'Se requiere usuario y clave de Excel')

    avisos = []
    reporte = _reporte_activo(slug)
    empresa, error = _empresa_de_la_consulta(usuario, request.GET.get('empresa'))
    if error:
        avisos.append(error)
    if not reporte:
        avisos.append(f'El reporte "{slug}" ya no existe o está inactivo')
    else:
        info = info_plantilla(slug)
        if info and request.GET.get('version') and request.GET.get('version') != info['version']:
            avisos.append('Hay una versión más nueva de esta plantilla; descárgala del portal (Reportes en Excel)')
    return JsonResponse({
        'usuario': usuario.get_full_name() or usuario.username,
        'empresa': empresa.pk if empresa else '',
        'nombre_empresa': empresa.nombre if empresa else '',
        'consultado': timezone.localtime().strftime('%d/%m/%Y %H:%M'),
        'aviso': ' | '.join(avisos) or 'Correcto',
    })


# ---------------------------------------------------------------- plantillas

def info_plantilla(slug):
    """Datos de la plantilla generada (versión, celdas de parámetros) o None si no hay plantilla."""
    archivo = CARPETA_PLANTILLAS / f'{slug}.json'
    if not archivo.exists() or not (CARPETA_PLANTILLAS / f'{slug}.xlsx').exists():
        return None
    return json.loads(archivo.read_text(encoding='utf-8'))


def _ruta_hoja(paquete, nombre_hoja):
    libro = paquete.read('xl/workbook.xml').decode('utf-8')
    relaciones = paquete.read('xl/_rels/workbook.xml.rels').decode('utf-8')
    hoja = re.search(r'<sheet [^>]*name="%s"[^>]*r:id="([^"]+)"' % re.escape(escape(nombre_hoja)), libro)
    destino = hoja and re.search(r'<Relationship [^>]*Id="%s"[^>]*Target="([^"]+)"' % hoja.group(1), relaciones)
    if not destino:
        destino = hoja and re.search(r'<Relationship [^>]*Target="([^"]+)"[^>]*Id="%s"' % hoja.group(1), relaciones)
    if not destino:
        raise ValueError(f'La plantilla no tiene la hoja {nombre_hoja}')
    ruta = destino.group(1).lstrip('/')
    return ruta if ruta.startswith('xl/') else 'xl/' + ruta


def _poner_celda(xml, ref, valor):
    """Reemplaza el contenido de una celda (que la plantilla deja vacía con formato) conservando su estilo."""
    patron = re.compile(r'<c r="%s"(?P<attrs>[^>]*?)(?:/>|>.*?</c>)' % ref, re.S)
    encontrada = patron.search(xml)
    if not encontrada:
        raise ValueError(f'La plantilla no tiene la celda {ref}')
    estilo = re.search(r'\ss="\d+"', encontrada.group('attrs'))
    estilo = estilo.group(0) if estilo else ''
    if isinstance(valor, date):
        nueva = f'<c r="{ref}"{estilo}><v>{(valor - date(1899, 12, 30)).days}</v></c>'
    else:
        nueva = f'<c r="{ref}"{estilo} t="inlineStr"><is><t xml:space="preserve">{escape(str(valor))}</t></is></c>'
    return xml[:encontrada.start()] + nueva + xml[encontrada.end():]


def plantilla_para_usuario(slug, valores):
    """Bytes del .xlsx de la plantilla con las celdas de parámetros llenas ({'servidor': ..., 'empresa': ...})."""
    info = info_plantilla(slug)
    original = (CARPETA_PLANTILLAS / f'{slug}.xlsx').read_bytes()
    salida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as paquete, zipfile.ZipFile(salida, 'w', zipfile.ZIP_DEFLATED) as nuevo:
        ruta = _ruta_hoja(paquete, info['hoja_parametros'])
        for elemento in paquete.infolist():
            contenido = paquete.read(elemento.filename)
            if elemento.filename == ruta:
                xml = contenido.decode('utf-8')
                for clave, ref in info['celdas'].items():
                    if clave in valores:
                        xml = _poner_celda(xml, ref, valores[clave])
                contenido = xml.encode('utf-8')
            elif elemento.filename == 'xl/workbook.xml':
                # Que Excel recalcule al abrir (títulos con fórmulas que usan los parámetros)
                xml = contenido.decode('utf-8')
                if 'fullCalcOnLoad' not in xml:
                    xml = xml.replace('<calcPr ', '<calcPr fullCalcOnLoad="1" ', 1) if '<calcPr ' in xml \
                        else xml.replace('</workbook>', '<calcPr fullCalcOnLoad="1"/></workbook>')
                contenido = xml.encode('utf-8')
            nuevo.writestr(elemento, contenido)
    return salida.getvalue()


# ---------------------------------------------------------------- páginas del portal

def _reportes_con_plantilla(usuario):
    reportes = []
    for reporte in Pivot_Dinamico.objects.filter(activo=True).order_by('orden', 'nombre'):
        info = info_plantilla(reporte.slug)
        if info and usuario_puede_ver_reporte(usuario, reporte):
            reportes.append({'reporte': reporte, 'version': info['version']})
    return reportes


@login_required
def inicio_excel_view(request):
    from rh.admin import admin_site
    context = admin_site.each_context(request)
    context.update({
        'title': 'Reportes en Excel',
        'reportes': _reportes_con_plantilla(request.user),
        'claves': ClaveExcel.objects.filter(usuario=request.user).order_by('-fecha_creacion'),
        'clave_nueva': request.session.pop('clave_excel_nueva', None),
        'usuario': request.user.username,
        'servidor': request.build_absolute_uri('/').rstrip('/'),
    })
    return render(request, 'reportes/excel_inicio.html', context)


@login_required
@require_POST
def nueva_clave_excel_view(request):
    _, clave = generar_clave(request.user, request.POST.get('nombre', ''))
    request.session['clave_excel_nueva'] = clave  # se muestra una sola vez
    return redirect('reportes:excel_inicio')


@login_required
@require_POST
def revocar_clave_excel_view(request, pk):
    clave = get_object_or_404(ClaveExcel, pk=pk, usuario=request.user)
    clave.activa = False
    clave.save(update_fields=['activa'])
    messages.success(request, f'Se desactivó la clave "{clave.nombre}". Los Excel que la usaban ya no podrán actualizar.')
    return redirect('reportes:excel_inicio')


@login_required
def descargar_plantilla_excel_view(request, slug):
    reporte = get_object_or_404(Pivot_Dinamico, slug=slug, activo=True)
    if not usuario_puede_ver_reporte(request.user, reporte) or not info_plantilla(slug):
        raise Http404
    empresa = getattr(request.user, '_empresa_activa', None) or ''
    permitidas = ', '.join(e.pk for e in empresas_permitidas(request.user))
    contenido = plantilla_para_usuario(slug, {
        'servidor': request.build_absolute_uri('/').rstrip('/'),
        'empresa': empresa,
        'empresas': f'Tus empresas: {permitidas}',
        'fecha_inicio': resolver_macro_fecha(reporte.fecha_inicio_macro or '-3m'),
        'fecha_fin': resolver_macro_fecha(reporte.fecha_fin_macro or 'm'),
    })
    nombre = re.sub(r'[^\w\- ]', '', reporte.nombre).strip() or slug
    respuesta = HttpResponse(contenido, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    respuesta['Content-Disposition'] = content_disposition_header(True, f'{nombre}{" - " + empresa if empresa else ""}.xlsx')
    return respuesta
