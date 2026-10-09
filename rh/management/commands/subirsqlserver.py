import os
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime
import pyodbc
from dotenv import load_dotenv
from supabase import create_client, Client
from django.core.management.base import BaseCommand


# 1. Localizar y cargar el .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

class Command(BaseCommand):
    help = 'Sincroniza los datos de SQL Server con Supabase (Opción 1: Inventario, Opción 2: FruDetalleVentas)'

    def add_arguments(self, parser):
        # Permite recibir un parámetro numérico para seleccionar la tabla
        parser.add_argument(
            '--tabla',
            '-t',
            type=int,
            default=1,
            help='1: Inventario (sp_frupa_inventario -> conc_eye_inventario)\n2: Detalle de Ventas (FruDetalleVentas -> FruDetalleVentas)'
        )

    def handle(self, *args, **options):
        opcion_tabla = options['tabla']

        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")

        SQL_SERVER = os.getenv("SQL_SERVER", "localhost")
        SQL_DATABASE = os.getenv("SQL_DATABASE")
        SQL_USER = os.getenv("SQL_USER")
        SQL_PASSWORD = os.getenv("SQL_PASSWORD")

        SQL_CONN_STR = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )

        if not SUPABASE_URL or not SUPABASE_KEY:
            self.stdout.write(self.style.ERROR("🔴 Faltan variables de Supabase en el .env"))
            return

        try:
            self.stdout.write("🟡 Conectando a SQL Server local...")
            conn = pyodbc.connect(SQL_CONN_STR)
            cursor = conn.cursor()

            # LÓGICA SEGÚN EL PARÁMETRO SELECCIONADO
            if opcion_tabla == 1:
                self.stdout.write("🟡 [Opción 1] Ejecutando sp_frupa_inventario...")
                query = (
                    "declare @FechaIni Datetime, @FechaFin Datetime "
                    "select @FechaFin = getdate() "
                    "select @FechaIni = d_inicio_tem from t_temporada where c_activo_tem = 1 "
                    "if @FechaIni is null begin set @FechaIni = dateadd(mm, -2, @FechaFin) end "
                    "exec sp_frupa_inventario @FechaIni, @FechaFin"
                )
                tabla_destino = "rep_eye_inventario"

            elif opcion_tabla == 2:
                self.stdout.write("🟡 [Opción 2] Consultando tabla FruDetalleVentas...")
                query = "exec AgroSmart_FRUSA.dbo.sp_fru_ventas_pivot '20130101', '20261231'"
                tabla_destino = "rep_detalleventas"

            else:
                self.stdout.write(self.style.ERROR(f"🔴 Opción inválida: {opcion_tabla}. Usa 1 o 2."))
                conn.close()
                return

            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                self.stdout.write(self.style.WARNING("🟠 No hay registros para sincronizar."))
                conn.close()
                return

            def serializar(val):
                if isinstance(val, Decimal): return float(val)
                if isinstance(val, (datetime, date)): return val.isoformat()
                return val

            columnas = [column[0] for column in cursor.description]
            datos_a_subir = [
                {col: serializar(val) for col, val in zip(columnas, row)}
                for row in rows
            ]
            conn.close()

            # Conexión y reemplazo en Supabase
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            self.stdout.write(f"🟡 Limpiando datos anteriores en Supabase ({tabla_destino})...")
            
            if opcion_tabla == 1:
                supabase.table(tabla_destino).delete().neq("c_codigo_tem", "00000000").execute()
            elif opcion_tabla == 2:
                # Se eliminan los registros utilizando una condición que siempre evalúa true
                supabase.table(tabla_destino).delete().neq("Factura", "____IMPOSIBLE_MATCH____").execute()

            self.stdout.write(f"🟡 Insertando nuevos datos en {tabla_destino}...")
            
            # Subida por lotes (batching de 1000 en 1000 por si la tabla de ventas es grande)
            batch_size = 1000
            for i in range(0, len(datos_a_subir), batch_size):
                batch = datos_a_subir[i:i + batch_size]
                supabase.table(tabla_destino).insert(batch).execute()

            self.stdout.write(self.style.SUCCESS(f"🟢 ¡Sincronización completada! Registros subidos a '{tabla_destino}': {len(datos_a_subir)}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"🔴 Error: {e}"))