from django.core.management.base import BaseCommand, CommandError

# La lógica vive en sincronizar_sqlserver.py (raíz del proyecto) para poder correrla sin Django
# en otro equipo (Windows Server con Python 3.10). Este comando solo la llama desde el portal.
from sincronizar_sqlserver import ESPECIALES, PROCESOS, sincronizar


class Command(BaseCommand):
    help = 'Sincroniza los datos de SQL Server con Supabase (Opción 1: Inventario, 2: FruDetalleVentas, 3: Proceso de maquila, 4: Cajas por empleado, 5: Pallets, 6: Catálogos de RH)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tabla',
            '-t',
            type=int,
            default=1,
            help='1: Inventario (sp_frupa_inventario -> rep_eye_inventario)\n2: Detalle de Ventas (sp_fru_ventas_pivot -> rep_detalleventas)\n'
                 '3: Proceso de maquila (t_palet vs recepción -> rep_proceso_maquila)\n'
                 '4: Cajas por empleado (t_controlcaja_pallet -> rep_cajas_empleado)\n'
                 '5: Pallets (t_palet -> rep_pallets)\n'
                 '6: Catálogos de RH (nómina nom10001/nom10003/nom10006 -> rh_empleado/rh_departamento/rh_puesto)'
        )
        parser.add_argument('--simular', action='store_true', help='Hace todo y lo deshace al final (solo proceso 6)')

    def handle(self, *args, **options):
        opcion = options['tabla']
        if opcion not in PROCESOS and opcion not in ESPECIALES:
            raise CommandError(f"Opción inválida: {opcion}. Usa {', '.join(map(str, list(PROCESOS) + list(ESPECIALES)))}.")
        try:
            sincronizar(opcion, salida=self.stdout.write, simular=options['simular'])
        except Exception as e:
            # Código de salida 1; el error ya quedó en rep_bitacora_sincronizacion
            raise CommandError(f"Error: {e}")
