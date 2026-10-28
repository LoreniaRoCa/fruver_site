from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from rh.admin import admin_site
from rh.models import Empleado
from . import logica
from .models import SolicitudVacaciones as Solicitud


# ---------------------------------------------------------------------------
# Accesos: los mismos usuarios y permisos del portal
#   Empleado  -> usuario ligado a un registro de rh_empleado
#   Jefe      -> empleado que aparece como id_jefe de otros
#   RH        -> permiso vacaciones.autorizar_rh
# ---------------------------------------------------------------------------
def es_rh(user):
    return user.is_superuser or user.has_perm('vacaciones.autorizar_rh')


def empleado_de(user):
    return Empleado.objects.select_related('id_jefe', 'id_puesto', 'id_departamento').filter(user=user).first()


def empresa_activa(request, empleado=None):
    return (request.session.get('empresa_activa') or request.session.get('empresa_id')
            or (empleado.empresa_id if empleado else None))


def contexto(request, **extra):
    ctx = admin_site.each_context(request)
    ctx.update(extra)
    return ctx


def jefe_que_autoriza(empleado):
    """El jefe inmediato solo da visto bueno si está activo y tiene usuario; si no, la solicitud va directo a RH."""
    jefe = empleado.id_jefe
    if jefe and jefe.estado_empleado == 'A' and jefe.user_id:
        return jefe
    return None


def puede_ver_solicitud(user, yo, solicitud):
    if es_rh(user):
        return True
    if not yo:
        return False
    return solicitud.empleado_id == yo.pk or solicitud.empleado.id_jefe_id == yo.pk


def parse_fecha(valor):
    try:
        return datetime.strptime(valor or '', '%Y-%m-%d').date()
    except ValueError:
        return None


def resumen_saldo(empleado):
    periodos = logica.periodos_derecho(empleado)
    derecho = sum((d for _, d in periodos), Decimal(0))
    consumen = list(logica.solicitudes_que_consumen(empleado).order_by('fecha_creacion', 'pk'))
    usados = sum((s.dias_habiles for s in consumen if s.estatus == Solicitud.APROBADA), Decimal(0))
    pendientes = sum((s.dias_habiles for s in consumen if s.estatus != Solicitud.APROBADA), Decimal(0))

    # Lo que queda de cada periodo después de descontar las solicitudes, del más antiguo al más reciente
    restantes = [[anio, dias] for anio, dias in periodos]
    for tomados in logica.repartir_en_periodos(periodos, [(s.pk, s.dias_habiles) for s in consumen]).values():
        for anio, dias in tomados:
            for fila in restantes:
                if fila[0] == anio:
                    fila[1] -= dias
                    break
    return {
        'anios': logica.anios_servicio(empleado.fechaalta),
        'derecho': derecho,
        'disfrutados': usados,
        'pendientes': pendientes,
        'disponibles': derecho - usados - pendientes,
        'periodos': [{'anio': a, 'dias': d, 'restan': r} for (a, d), (_, r) in zip(periodos, restantes)],
    }


# ---------------------------------------------------------------------------
# Mis vacaciones / detalle de un empleado (RH)
# ---------------------------------------------------------------------------
@login_required
def mis_vacaciones_view(request, empleado_pk=None):
    yo = empleado_de(request.user)
    if empleado_pk:
        if not es_rh(request.user):
            raise PermissionDenied
        empleado = get_object_or_404(Empleado.objects.select_related('id_jefe', 'id_puesto', 'id_departamento'), pk=empleado_pk)
    else:
        if not yo:
            if es_rh(request.user):
                return redirect('vacaciones:personal')
            messages.error(request, "Tu usuario no está vinculado a ningún registro de Empleado.")
            return redirect('dashboard_modulos')
        empleado = yo

    solicitudes = Solicitud.objects.filter(empleado=empleado).select_related('jefe', 'decidido_por')
    pagina = Paginator(solicitudes, 25).get_page(request.GET.get('page'))

    return render(request, 'vacaciones/mis_vacaciones.html', contexto(
        request,
        empleado=empleado,
        es_propio=empleado == yo,
        saldo=resumen_saldo(empleado),
        pagina=pagina,
        jefe=jefe_que_autoriza(empleado),
        es_rh=es_rh(request.user),
    ))


# ---------------------------------------------------------------------------
# Nueva solicitud
# ---------------------------------------------------------------------------
def empleados_para_captura(request, yo):
    empresa = empresa_activa(request, yo)
    return Empleado.objects.filter(empresa_id=empresa, estado_empleado='A').order_by('nombre_largo')


@login_required
def solicitar_view(request):
    yo = empleado_de(request.user)
    rh = es_rh(request.user)
    if not yo and not rh:
        messages.error(request, "Tu usuario no está vinculado a ningún registro de Empleado.")
        return redirect('dashboard_modulos')

    empleados = empleados_para_captura(request, yo) if rh else None
    datos = {'empleado': (request.GET.get('empleado') if rh else '') or (str(yo.pk) if yo else ''),
             'fecha_inicio': '', 'fecha_fin': '', 'motivo': ''}

    if request.method == 'POST':
        datos = {k: request.POST.get(k, '').strip() for k in datos}
        empleado = yo
        if rh and datos['empleado'] and (not yo or datos['empleado'] != str(yo.pk)):
            empleado = get_object_or_404(empleados, pk=datos['empleado'])
        if empleado is None:
            messages.error(request, "Selecciona a la persona.")
        else:
            try:
                solicitud = crear_solicitud(request.user, yo, empleado, parse_fecha(datos['fecha_inicio']),
                                            parse_fecha(datos['fecha_fin']), datos['motivo'])
            except ValueError as error:
                messages.error(request, str(error))
            else:
                if solicitud.estatus == Solicitud.APROBADA:
                    messages.success(request, f"Formato {solicitud.folio_texto} generado y autorizado por RH.")
                    return redirect('vacaciones:formato', pk=solicitud.pk)
                destino = "tu jefe inmediato" if solicitud.estatus == Solicitud.PENDIENTE_JEFE else "Recursos Humanos"
                messages.success(request, f"Solicitud {solicitud.folio_texto} enviada. Queda pendiente de {destino}.")
                return redirect('vacaciones:mis_vacaciones')

    return render(request, 'vacaciones/solicitar.html', contexto(
        request,
        yo=yo,
        es_rh=rh,
        empleados=empleados,
        datos=datos,
        saldo=resumen_saldo(yo) if yo else None,
        hoy=date.today().isoformat(),
    ))


def crear_solicitud(user, yo, empleado, inicio, fin, motivo):
    capturada_por_rh = empleado != yo  # RH captura el formato de otra persona: queda autorizado
    calendario = logica.Calendario(empleado.empresa_id)
    ahora = timezone.now()
    for _ in range(3):  # reintento por si dos personas toman el mismo folio al mismo tiempo
        try:
            with transaction.atomic():
                dias, extraordinaria = logica.validar_solicitud(empleado, inicio, fin, calendario)
                solicitud = Solicitud(
                    empresa_id=empleado.empresa_id,
                    serie=calendario.politica.serie_folio,
                    folio=logica.siguiente_folio(empleado.empresa_id),
                    empleado=empleado,
                    fecha_inicio=inicio,
                    fecha_fin=fin,
                    dias_habiles=dias,
                    motivo=motivo,
                    extraordinaria=extraordinaria,
                    capturada_por=user,
                    fecha_creacion=ahora,
                )
                if capturada_por_rh:
                    solicitud.estatus = Solicitud.APROBADA
                    solicitud.decidido_por = user
                    solicitud.fecha_decision = ahora
                    solicitud.nota_decision = "Formato generado por Recursos Humanos."
                else:
                    solicitud.jefe = jefe_que_autoriza(empleado)
                    solicitud.estatus = Solicitud.PENDIENTE_JEFE if solicitud.jefe else Solicitud.PENDIENTE_RH
                solicitud.save()
                return solicitud
        except IntegrityError:
            continue
    raise ValueError("No se pudo asignar folio, intenta de nuevo.")


@login_required
def calcular_view(request):
    """Vista previa para el formulario: días hábiles, caso extraordinario y periodos que se descuentan."""
    yo = empleado_de(request.user)
    empleado = yo
    pk = request.GET.get('empleado')
    if pk and (not yo or pk != str(yo.pk)):
        if not es_rh(request.user):
            raise PermissionDenied
        empleado = get_object_or_404(empleados_para_captura(request, yo), pk=pk)
    if not empleado:
        return JsonResponse({'error': 'Selecciona a la persona.'})

    saldo = resumen_saldo(empleado)
    respuesta = {'disponibles': logica.formatear_dias(saldo['disponibles'])}
    inicio, fin = parse_fecha(request.GET.get('inicio')), parse_fecha(request.GET.get('fin'))
    if not inicio or not fin:
        return JsonResponse(respuesta)
    try:
        dias, extraordinaria = logica.validar_solicitud(empleado, inicio, fin)
    except ValueError as error:
        respuesta['error'] = str(error)
        return JsonResponse(respuesta)
    calendario = logica.Calendario(empleado.empresa_id)
    respuesta.update({
        'dias': dias,
        'extraordinaria': extraordinaria,
        'regreso': calendario.siguiente_dia_habil(fin).isoformat(),
        'cargo': [{'anio': a, 'dias': logica.formatear_dias(d)} for a, d in logica.vista_previa_cargo(empleado, dias)],
        'quedan': logica.formatear_dias(saldo['disponibles'] - dias),
    })
    return JsonResponse(respuesta)


# ---------------------------------------------------------------------------
# Aprobaciones (jefe inmediato -> RH)
# ---------------------------------------------------------------------------
def alcance_aprobaciones(request, yo):
    """Solicitudes que este usuario puede autorizar: las de su equipo y, si es RH, todas las de la empresa."""
    filtro = Q(pk__in=[])
    if yo:
        filtro |= Q(empleado__id_jefe=yo)
    if es_rh(request.user):
        filtro |= Q(empresa_id=empresa_activa(request, yo))
    return Solicitud.objects.filter(filtro).select_related('empleado', 'empleado__id_puesto', 'empleado__id_departamento', 'jefe', 'decidido_por')


@login_required
def aprobaciones_view(request):
    yo = empleado_de(request.user)
    rh = es_rh(request.user)
    alcance = alcance_aprobaciones(request, yo)

    pendientes_filtro = Q(pk__in=[])
    if yo:
        pendientes_filtro |= Q(estatus=Solicitud.PENDIENTE_JEFE, empleado__id_jefe=yo)
    if rh:
        pendientes_filtro |= Q(estatus=Solicitud.PENDIENTE_RH)
    pendientes = alcance.filter(pendientes_filtro).order_by('fecha_inicio')
    # RH ve también lo que sigue esperando al jefe, para dar seguimiento
    en_espera_jefe = alcance.filter(estatus=Solicitud.PENDIENTE_JEFE).exclude(empleado__id_jefe=yo).order_by('fecha_inicio') if rh else []
    resueltas = alcance.exclude(estatus__in=[Solicitud.PENDIENTE_JEFE, Solicitud.PENDIENTE_RH]).filter(liquidada=False)[:30]

    return render(request, 'vacaciones/aprobaciones.html', contexto(
        request,
        yo=yo,
        es_rh=rh,
        es_jefe=bool(yo and Empleado.objects.filter(id_jefe=yo, estado_empleado='A').exists()),
        pendientes=pendientes,
        en_espera_jefe=en_espera_jefe,
        resueltas=resueltas,
    ))


@login_required
@require_POST
def accion_view(request, pk):
    yo = empleado_de(request.user)
    rh = es_rh(request.user)
    accion = request.POST.get('accion')
    nota = request.POST.get('nota', '').strip()
    regresar = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(regresar, allowed_hosts={request.get_host()}):
        regresar = 'vacaciones:aprobaciones'

    with transaction.atomic():
        solicitud = get_object_or_404(Solicitud.objects.select_for_update().select_related('empleado'), pk=pk)
        es_su_jefe = bool(yo and solicitud.empleado.id_jefe_id == yo.pk)
        ahora = timezone.now()
        try:
            if accion == 'cancelar':
                if not yo or solicitud.empleado_id != yo.pk:
                    raise ValueError("Solo puedes cancelar tus propias solicitudes.")
                if not solicitud.esta_pendiente:
                    raise ValueError("Solo se pueden cancelar solicitudes pendientes.")
                solicitud.estatus = Solicitud.CANCELADA
                solicitud.decidido_por = request.user
                solicitud.fecha_decision = ahora
                solicitud.nota_decision = "Cancelada por la persona solicitante."
                mensaje = f"Solicitud {solicitud.folio_texto} cancelada."

            elif accion == 'rechazar':
                if len(nota) < 8:
                    raise ValueError("Al rechazar, indica el motivo (mínimo 8 caracteres).")
                if not ((es_su_jefe and solicitud.estatus == Solicitud.PENDIENTE_JEFE)
                        or (rh and solicitud.estatus == Solicitud.PENDIENTE_RH)):
                    raise ValueError("No puedes rechazar esta solicitud en esta etapa.")
                solicitud.estatus = Solicitud.RECHAZADA
                solicitud.decidido_por = request.user
                solicitud.fecha_decision = ahora
                solicitud.nota_decision = nota
                mensaje = f"Solicitud {solicitud.folio_texto} rechazada."

            elif accion == 'aprobar' and solicitud.estatus == Solicitud.PENDIENTE_JEFE:
                if not es_su_jefe:
                    raise ValueError("El primer visto bueno corresponde al jefe inmediato.")
                solicitud.estatus = Solicitud.PENDIENTE_RH
                solicitud.jefe = yo
                solicitud.fecha_visto_jefe = ahora
                solicitud.nota_jefe = nota or "Visto bueno del jefe inmediato."
                mensaje = f"Visto bueno registrado. {solicitud.folio_texto} pasa a Recursos Humanos."

            elif accion == 'aprobar' and solicitud.estatus == Solicitud.PENDIENTE_RH:
                if not rh:
                    raise ValueError("El segundo visto bueno corresponde a Recursos Humanos.")
                solicitud.estatus = Solicitud.APROBADA
                solicitud.decidido_por = request.user
                solicitud.fecha_decision = ahora
                solicitud.nota_decision = nota or "Aprobada por Recursos Humanos."
                mensaje = f"Solicitud {solicitud.folio_texto} autorizada."

            else:
                raise ValueError("Esta solicitud ya fue resuelta.")
        except ValueError as error:
            messages.error(request, str(error))
            return redirect(regresar)
        solicitud.save()

    messages.success(request, mensaje)
    return redirect(regresar)


# ---------------------------------------------------------------------------
# Formato imprimible
# ---------------------------------------------------------------------------
@login_required
def formato_view(request, pk):
    solicitud = get_object_or_404(
        Solicitud.objects.select_related('empleado', 'empleado__id_puesto', 'empleado__id_departamento', 'empleado__id_jefe', 'jefe', 'empresa'),
        pk=pk,
    )
    if not puede_ver_solicitud(request.user, empleado_de(request.user), solicitud):
        raise PermissionDenied

    empleado = solicitud.empleado
    calendario = logica.Calendario(solicitud.empresa_id)
    derecho = logica.dias_derecho(empleado)
    disfrutados = logica.dias_disfrutados(empleado, excluir_id=solicitud.pk)
    disponibles = derecho - disfrutados
    observaciones = " ".join(filter(None, [
        solicitud.motivo,
        f"Jefe: {solicitud.nota_jefe}" if solicitud.nota_jefe else "",
        f"RH: {solicitud.nota_decision}" if solicitud.nota_decision else "",
    ]))
    jefe = solicitud.jefe or empleado.id_jefe

    return render(request, 'vacaciones/formato.html', contexto(
        request,
        s=solicitud,
        empleado=empleado,
        anios=logica.anios_servicio(empleado.fechaalta, solicitud.fecha_inicio),
        derecho=derecho,
        disfrutados=disfrutados,
        disponibles=disponibles,
        actualizados=disponibles - solicitud.dias_habiles,
        cargo=[(a, logica.formatear_dias(d)) for a, d in logica.cargo_de_solicitud(solicitud)] if not solicitud.liquidada else [],
        regreso=calendario.siguiente_dia_habil(solicitud.fecha_fin),
        emision=(solicitud.fecha_decision or solicitud.fecha_creacion),
        observaciones=observaciones,
        nombre_jefe=jefe.nombre_largo if jefe else "Jefe inmediato",
        responsable_rh=calendario.politica.responsable_rh,
    ))


# ---------------------------------------------------------------------------
# RH: saldos y solicitudes de todo el personal
# ---------------------------------------------------------------------------
def requiere_rh(request):
    if not es_rh(request.user):
        raise PermissionDenied


@login_required
def personal_view(request):
    requiere_rh(request)
    empresa = empresa_activa(request, empleado_de(request.user))
    empleados = (Empleado.objects.filter(empresa_id=empresa, estado_empleado='A')
                 .select_related('id_departamento', 'id_puesto', 'saldo_vacaciones').order_by('nombre_largo'))

    # Una sola consulta para lo que consumen todas las solicitudes vigentes
    consumos = {}
    for emp_id, estatus, dias in (Solicitud.objects.filter(empresa_id=empresa, liquidada=False, estatus__in=Solicitud.ESTATUS_CONSUMEN)
                                  .values_list('empleado_id', 'estatus', 'dias_habiles')):
        fila = consumos.setdefault(emp_id, [Decimal(0), Decimal(0)])
        fila[0 if estatus == Solicitud.APROBADA else 1] += dias

    filas = []
    for emp in empleados:
        derecho = logica.dias_derecho(emp)
        disfrutados, pendientes = consumos.get(emp.pk, [Decimal(0), Decimal(0)])
        filas.append({
            'emp': emp,
            'anios': logica.anios_servicio(emp.fechaalta),
            'derecho': derecho,
            'disfrutados': disfrutados,
            'pendientes': pendientes,
            'disponibles': derecho - disfrutados - pendientes,
            'sin_saldo': not hasattr(emp, 'saldo_vacaciones'),
        })

    return render(request, 'vacaciones/personal.html', contexto(request, filas=filas))


@login_required
def solicitudes_view(request):
    requiere_rh(request)
    empresa = empresa_activa(request, empleado_de(request.user))
    qs = Solicitud.objects.filter(empresa_id=empresa).select_related('empleado', 'empleado__id_departamento')

    filtros = {k: request.GET.get(k, '').strip() for k in ('q', 'estatus', 'anio')}
    if filtros['q']:
        q = filtros['q']
        condicion = Q(empleado__nombre_largo__icontains=q)
        if q.isdigit():
            condicion |= Q(folio=int(q)) | Q(empleado__id_empleado=int(q))
        qs = qs.filter(condicion)
    if filtros['estatus']:
        qs = qs.filter(estatus=filtros['estatus'])
    if filtros['anio'].isdigit():
        qs = qs.filter(fecha_inicio__year=int(filtros['anio']))

    pagina = Paginator(qs, 50).get_page(request.GET.get('page'))
    parametros = request.GET.copy()
    parametros.pop('page', None)
    anios = range(date.today().year + 1, 2016, -1)

    return render(request, 'vacaciones/solicitudes.html', contexto(
        request, pagina=pagina, filtros=filtros, estatus=Solicitud.ESTATUS, anios=anios,
        parametros=parametros.urlencode(),
    ))
