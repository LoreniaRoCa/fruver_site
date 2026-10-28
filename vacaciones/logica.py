"""
Reglas de vacaciones (portadas de lft.ts, dates.ts y vacations.ts del sistema en Next.js).

- Tabla de la empresa hasta 2022 y desde 2023 (el aniversario define cuál aplica).
- Domingo, días inhábiles y (si la política lo dice) sábado no descuentan.
- El saldo es: días al corte + aniversarios cumplidos después del corte − solicitudes
  pendientes o aprobadas que no estén liquidadas.
- Las solicitudes consumen del periodo más antiguo al más reciente.
"""
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from .models import DiaInhabil, PoliticaVacaciones, SaldoVacaciones, SolicitudVacaciones

# (desde, hasta, días) por años de servicio cumplidos
TABLA_EMPRESA_HASTA_2022 = [
    (1, 4, 12), (5, 9, 14), (10, 14, 16), (15, 19, 18), (20, 24, 20),
    (25, 25, 28), (26, 30, 30), (31, 34, 32),
]
TABLA_EMPRESA_DESDE_2023 = [
    (1, 1, 12), (2, 2, 14), (3, 3, 16), (4, 4, 18), (5, 5, 20),
    (6, 10, 22), (11, 15, 24), (16, 20, 26), (21, 25, 28), (26, 30, 30),
    (31, 35, 32), (36, 40, 34), (41, 45, 36), (46, 50, 38), (51, 55, 40),
]


def _buscar_banda(tabla, anios):
    for desde, hasta, dias in tabla:
        if desde <= anios <= hasta:
            return dias
    ultimo_hasta, ultimo_dias = tabla[-1][1], tabla[-1][2]
    if anios > ultimo_hasta:
        bandas = (anios - ultimo_hasta - 1) // 5 + 1
        return ultimo_dias + bandas * 2
    return 0


def _aniversario(fecha_alta, anios):
    return fecha_alta + relativedelta(years=anios)


def dias_por_anio_cumplido(fecha_alta, anios):
    """Días que se suman al cumplir ese año de servicio."""
    if anios < 1 or not fecha_alta:
        return 0
    tabla = TABLA_EMPRESA_HASTA_2022 if _aniversario(fecha_alta, anios) < date(2023, 1, 1) else TABLA_EMPRESA_DESDE_2023
    return _buscar_banda(tabla, anios)


def anios_servicio(fecha_alta, hoy=None):
    if not fecha_alta:
        return 0
    hoy = hoy or date.today()
    return max(0, relativedelta(hoy, fecha_alta).years)


# ---------------------------------------------------------------------------
# Política y días hábiles
# ---------------------------------------------------------------------------
class Calendario:
    """Política de la empresa con sus días inhábiles ya cargados."""

    def __init__(self, empresa_id):
        self.politica = PoliticaVacaciones.objects.filter(empresa_id=empresa_id).first() or PoliticaVacaciones(empresa_id=empresa_id)
        self.inhabiles = dict(DiaInhabil.objects.filter(empresa_id=empresa_id).values_list('fecha', 'nombre'))

    def es_habil(self, dia):
        if dia.weekday() == 6:
            return False
        if dia.weekday() == 5 and not self.politica.sabado_habil:
            return False
        return dia not in self.inhabiles

    def contar_dias(self, inicio, fin):
        if fin < inicio:
            return 0
        return sum(1 for n in range((fin - inicio).days + 1) if self.es_habil(inicio + timedelta(days=n)))

    def siguiente_dia_habil(self, dia):
        cursor = dia + timedelta(days=1)
        for _ in range(14):
            if self.es_habil(cursor):
                return cursor
            cursor += timedelta(days=1)
        return cursor


# ---------------------------------------------------------------------------
# Saldos
# ---------------------------------------------------------------------------
def obtener_saldo(empleado, hoy=None):
    """
    Saldo al corte. Si RH no ha capturado uno, solo se reconoce el periodo del último
    aniversario cumplido (no se suman todos los años desde el alta, que no sabemos si ya se gozaron).
    """
    try:
        return empleado.saldo_vacaciones
    except SaldoVacaciones.DoesNotExist:
        anios = anios_servicio(empleado.fechaalta, hoy)
        return SaldoVacaciones(empleado=empleado, dias_arrastrados=Decimal(0), anios_acumulados=max(anios - 1, 0))


def periodos_derecho(empleado, hoy=None):
    """[(año, días)] del más antiguo al más reciente."""
    saldo = obtener_saldo(empleado, hoy)
    alta = empleado.fechaalta
    anios = anios_servicio(alta, hoy)
    periodos = []
    if saldo.dias_arrastrados > 0:
        anio_corte = alta.year + (saldo.anios_acumulados or anios) if alta else (hoy or date.today()).year
        periodos.append([anio_corte, Decimal(saldo.dias_arrastrados)])
    for n in range(saldo.anios_acumulados + 1, anios + 1):
        dias = dias_por_anio_cumplido(alta, n)
        if dias > 0:
            periodos.append([alta.year + n, Decimal(dias)])
    return periodos


def dias_derecho(empleado, hoy=None):
    return sum((dias for _, dias in periodos_derecho(empleado, hoy)), Decimal(0))


def solicitudes_que_consumen(empleado, excluir_id=None):
    qs = SolicitudVacaciones.objects.filter(
        empleado=empleado, estatus__in=SolicitudVacaciones.ESTATUS_CONSUMEN, liquidada=False,
    )
    if excluir_id:
        qs = qs.exclude(pk=excluir_id)
    return qs


def dias_usados(empleado, excluir_id=None):
    return sum((s.dias_habiles for s in solicitudes_que_consumen(empleado, excluir_id)), Decimal(0))


def dias_disfrutados(empleado, excluir_id=None):
    return sum(
        (s.dias_habiles for s in solicitudes_que_consumen(empleado, excluir_id).filter(estatus=SolicitudVacaciones.APROBADA)),
        Decimal(0),
    )


def dias_disponibles(empleado):
    return dias_derecho(empleado) - dias_usados(empleado)


def repartir_en_periodos(periodos, consumos):
    """consumos: [(id, días)] en orden. Devuelve {id: [(año, días)]}."""
    restantes = [[anio, dias] for anio, dias in periodos]
    resultado = {}
    for ident, dias in consumos:
        faltan = Decimal(dias)
        tomados = []
        for periodo in restantes:
            if faltan <= 0:
                break
            usar = min(periodo[1], faltan)
            if usar <= 0:
                continue
            tomados.append((periodo[0], usar))
            periodo[1] -= usar
            faltan -= usar
        resultado[ident] = tomados
    return resultado


def cargo_de_solicitud(solicitud):
    """De qué periodos se descuenta la solicitud: [(año, días)]."""
    consumos = [
        (s.pk, s.dias_habiles)
        for s in solicitudes_que_consumen(solicitud.empleado).order_by('fecha_creacion', 'pk')
    ]
    return repartir_en_periodos(periodos_derecho(solicitud.empleado), consumos).get(solicitud.pk, [])


def vista_previa_cargo(empleado, dias):
    consumos = [(s.pk, s.dias_habiles) for s in solicitudes_que_consumen(empleado).order_by('fecha_creacion', 'pk')]
    consumos.append(('nueva', dias))
    return repartir_en_periodos(periodos_derecho(empleado), consumos).get('nueva', [])


# ---------------------------------------------------------------------------
# Validación de nuevas solicitudes
# ---------------------------------------------------------------------------
def validar_solicitud(empleado, inicio, fin, calendario=None, hoy=None):
    """Devuelve (dias_habiles, extraordinaria) o lanza ValueError con el mensaje para el usuario."""
    hoy = hoy or date.today()
    calendario = calendario or Calendario(empleado.empresa_id)
    if not inicio or not fin:
        raise ValueError("Selecciona el periodo de vacaciones.")
    if fin < inicio:
        raise ValueError("La fecha de fin no puede ser anterior a la de inicio.")

    dias = calendario.contar_dias(inicio, fin)
    if dias < 1:
        raise ValueError("El periodo no incluye días hábiles (lunes a sábado, menos inhábiles y domingo).")

    disponibles = dias_disponibles(empleado)
    if dias > disponibles:
        plural = "" if disponibles == 1 else "s"
        raise ValueError(f"Solo hay {formatear_dias(disponibles)} día{plural} disponible{plural}.")

    encimada = SolicitudVacaciones.objects.filter(
        empleado=empleado, estatus__in=SolicitudVacaciones.ESTATUS_CONSUMEN,
        fecha_inicio__lte=fin, fecha_fin__gte=inicio,
    ).exists()
    if encimada:
        raise ValueError("Ya hay una solicitud pendiente o aprobada en esas fechas.")

    extraordinaria = (inicio - hoy).days < calendario.politica.dias_aviso_minimo
    return dias, extraordinaria


def siguiente_folio(empresa_id):
    ultimo = SolicitudVacaciones.objects.filter(empresa_id=empresa_id).order_by('-folio').values_list('folio', flat=True).first()
    return (ultimo or 0) + 1


def formatear_dias(valor):
    valor = Decimal(valor)
    return str(int(valor)) if valor == valor.to_integral_value() else str(valor.normalize())
