import os
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime
import pyodbc
from dotenv import load_dotenv
from supabase import create_client, Client
from django.core.management.base import BaseCommand
from django.db import connection  # Permite ejecutar sentencias SQL directas en Supabase


# 1. Localizar y cargar el .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

class Command(BaseCommand):
    help = 'Sincroniza los datos de SQL Server con Supabase (Opción 1: Inventario, Opción 2: FruDetalleVentas)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tabla',
            '-t',
            type=int,
            default=1,
            help='1: Inventario (sp_frupa_inventario -> rep_eye_inventario)\n2: Detalle de Ventas (sp_fru_ventas_pivot -> rep_detalleventas)'
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

            # Declaración de variables para el limpiado específico por fechas
            f_ini_str = None
            f_fin_str = None
            campo_fecha = None  # Nombre de la columna de fecha en la tabla de Supabase

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
                # Si la opción 1 requiere limpiar toda la tabla, se mantendrá sin rango de fechas

            elif opcion_tabla == 2:
                # 🟢 DEFINICIÓN DEL RANGO DE FECHAS
                f_ini_str = "2026-01-01"
                f_fin_str = "2026-12-31"
                campo_fecha = "FechaFac"  # ⚠️ Ajusta al nombre exacto de la columna de fecha en Supabase (ej. 'fecha', 'd_fecha', etc.)

                # Formato YYYYMMDD para el Stored Procedure de SQL Server
                f_ini_sql = f_ini_str.replace("-", "")
                f_fin_sql = f_fin_str.replace("-", "")

                self.stdout.write(f"🟡 [Opción 2] Consultando tabla FruDetalleVentas ({f_ini_str} al {f_fin_str})...")
                query = f"exec AgroSmart_FRUSA.dbo.sp_fru_ventas_pivot '{f_ini_sql}', '{f_fin_sql}', 1"
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

            # 🟢 LIMPIADO SELECTIVO EN SUPABASE
            with connection.cursor() as db_cursor:
                if f_ini_str and f_fin_str and campo_fecha:
                    self.stdout.write(f"🟡 Eliminando datos anteriores en Supabase ({tabla_destino}) entre {f_ini_str} y {f_fin_str}...")
                    delete_sql = f'DELETE FROM public."{tabla_destino}" WHERE "{campo_fecha}"::date BETWEEN %s AND %s;'
                    db_cursor.execute(delete_sql, [f_ini_str, f_fin_str])
                else:
                    self.stdout.write(f"🟡 Limpiando toda la tabla en Supabase ({tabla_destino}) mediante TRUNCATE...")
                    db_cursor.execute(f'TRUNCATE TABLE public."{tabla_destino}" RESTART IDENTITY;')

            # Conexión e inserción masiva en Supabase
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            self.stdout.write(f"🟡 Insertando nuevos datos en {tabla_destino} ({len(datos_a_subir)} registros)...")
            
            # Subida por lotes (batching de 500 en 500 para evitar sobrecargar payloads HTTP)
            batch_size = 500
            for i in range(0, len(datos_a_subir), batch_size):
                batch = datos_a_subir[i:i + batch_size]
                supabase.table(tabla_destino).insert(batch).execute()

            self.stdout.write(self.style.SUCCESS(f"🟢 ¡Sincronización completada! Registros subidos a '{tabla_destino}': {len(datos_a_subir)}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"🔴 Error: {e}"))