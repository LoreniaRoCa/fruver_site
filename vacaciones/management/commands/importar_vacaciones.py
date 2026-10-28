"""
Importa saldos y solicitudes históricas del sistema de vacaciones en Next.js.

    python manage.py importar_vacaciones --empresa FRUSA \
        --catchup "C:/.../src/lib/vacation-catchup.json" \
        --saldos "C:/.../src/lib/balance-sync.json" --simular

- Liga a cada persona con rh_empleado por número de empleado (id_empleado) dentro de la empresa.
- Saldo al corte: `availableDays` de balance-sync (el más reciente) o, si no está, `carriedDays`
  del catch-up. Los años ya incluidos son los cumplidos a la fecha de importación, igual que
  hacía el sistema anterior al anclar saldos.
- Las solicitudes históricas se guardan como aprobadas y liquidadas (ya descontadas en el saldo).
- Se puede volver a correr: no duplica folios y actualiza los saldos.
"""
import json
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from rh.models import Empleado, Empresa
from vacaciones.logica import anios_servicio
from vacaciones.models import DiaInhabil, PoliticaVacaciones, SaldoVacaciones, SolicitudVacaciones

DIAS_INHABILES_2026 = [
    ('2026-01-01', 'Año Nuevo'),
    ('2026-02-02', 'Día de la Constitución'),
    ('2026-03-16', 'Natalicio de Benito Juárez'),
    ('2026-05-01', 'Día del Trabajo'),
    ('2026-09-16', 'Independencia'),
    ('2026-11-16', 'Revolución Mexicana'),
    ('2026-12-25', 'Navidad'),
]


def leer_json(ruta):
    try:
        with open(ruta, encoding='utf-8') as archivo:
            return json.load(archivo)
    except (OSError, ValueError) as error:
        raise CommandError(f"No se pudo leer {ruta}: {error}")


def fecha_iso(valor):
    return datetime.strptime(valor[:10], '%Y-%m-%d').date()


class Command(BaseCommand):
    help = "Importa saldos y solicitudes históricas del sistema de vacaciones anterior (Next.js)."

    def add_arguments(self, parser):
        parser.add_argument('--empresa', required=True, help="id_empresa, ej. FRUSA")
        parser.add_argument('--catchup', required=True, help="Ruta a vacation-catchup.json")
        parser.add_argument('--saldos', help="Ruta a balance-sync.json (saldos más recientes)")
        parser.add_argument('--responsable-rh', default='Alejandra Borbón Duarte',
                            help="Nombre para la firma de RH en el formato, si la política no tiene uno")
        parser.add_argument('--simular', action='store_true', help="Muestra lo que haría sin guardar nada")

    def handle(self, *args, **opciones):
        empresa = Empresa.objects.filter(pk=opciones['empresa']).first()
        if not empresa:
            raise CommandError(f"No existe la empresa {opciones['empresa']}")

        catchup = leer_json(opciones['catchup'])
        sync = {r['employeeNumber']: r for r in leer_json(opciones['saldos'])} if opciones['saldos'] else {}

        empleados = {}
        for emp in Empleado.objects.filter(empresa=empresa):
            empleados[str(emp.id_empleado)] = emp

        hoy = date.today()
        sin_empleado = []
        saldos = []
        for persona in catchup['people']:
            emp = empleados.get(persona['employeeNumber'])
            if not emp:
                sin_empleado.append(f"#{persona['employeeNumber']} {persona['name']} ({persona['status']})")
                continue
            fila_sync = sync.get(persona['employeeNumber'])
            dias = fila_sync['availableDays'] if fila_sync else persona.get('carriedDays', persona.get('availableDays', 0))
            alta = emp.fechaalta or fecha_iso(persona['hireDate'])
            saldos.append((emp, Decimal(str(dias)), anios_servicio(alta, hoy)))

        # Personas que solo vienen en el archivo de saldos (no estaban en el catch-up)
        en_catchup = {p['employeeNumber'] for p in catchup['people']}
        for numero, fila_sync in sync.items():
            if numero in en_catchup:
                continue
            emp = empleados.get(numero)
            if not emp:
                sin_empleado.append(f"#{numero} (solo en archivo de saldos)")
                continue
            saldos.append((emp, Decimal(str(fila_sync['availableDays'])), anios_servicio(emp.fechaalta, hoy)))

        existentes = set(SolicitudVacaciones.objects.filter(empresa=empresa).values_list('folio', flat=True))
        nuevas, sin_empleado_solicitudes = [], 0
        for r in catchup['requests']:
            emp = empleados.get(r['employeeNumber'])
            if not emp:
                sin_empleado_solicitudes += 1
                continue
            if r['folio'] in existentes:
                continue
            creada = timezone.make_aware(datetime.strptime(r['createdAt'][:19], '%Y-%m-%dT%H:%M:%S'), dt_timezone.utc)
            nuevas.append(SolicitudVacaciones(
                empresa=empresa, serie='A', folio=r['folio'], empleado=emp,
                fecha_inicio=fecha_iso(r['startDate']), fecha_fin=fecha_iso(r['endDate']),
                dias_habiles=Decimal(str(r['businessDays'])), motivo=r.get('reason') or '',
                estatus=SolicitudVacaciones.APROBADA, liquidada=True,
                fecha_creacion=creada, fecha_decision=creada,
                nota_decision='Registro histórico importado del sistema anterior.',
            ))

        self.stdout.write(f"Empresa {empresa}: {len(empleados)} empleados en rh_empleado")
        self.stdout.write(f"Saldos a guardar: {len(saldos)} (archivo catch-up: {len(catchup['people'])} personas; archivo de saldos: {len(sync)})")
        self.stdout.write(f"Solicitudes nuevas: {len(nuevas)} (ya existían {len(existentes)}; sin empleado: {sin_empleado_solicitudes})")
        if sin_empleado:
            self.stdout.write(self.style.WARNING(f"{len(sin_empleado)} personas sin registro en rh_empleado (no se importan):"))
            for texto in sin_empleado:
                self.stdout.write(f"   {texto}")

        if opciones['simular']:
            self.stdout.write(self.style.NOTICE("Simulación: no se guardó nada."))
            return

        with transaction.atomic():
            politica, _ = PoliticaVacaciones.objects.get_or_create(empresa=empresa)
            if not politica.responsable_rh:
                politica.responsable_rh = opciones['responsable_rh']
                politica.save()
            for fecha, nombre in DIAS_INHABILES_2026:
                DiaInhabil.objects.get_or_create(empresa=empresa, fecha=fecha_iso(fecha), defaults={'nombre': nombre})
            for emp, dias, anios in saldos:
                SaldoVacaciones.objects.update_or_create(
                    empleado=emp, defaults={'dias_arrastrados': dias, 'anios_acumulados': anios, 'fecha_corte': hoy})
            SolicitudVacaciones.objects.bulk_create(nuevas, batch_size=500)

        self.stdout.write(self.style.SUCCESS("Importación terminada."))
