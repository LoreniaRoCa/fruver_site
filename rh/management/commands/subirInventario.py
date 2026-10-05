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
    help = 'Sincroniza los datos de SQL Server con Supabase'

    def handle(self, *args, **kwargs):
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

            self.stdout.write("🟡 Ejecutando procedimiento almacenado...")
            cursor.execute("declare @FechaIni Datetime, @FechaFin Datetime " +
                        "select @FechaFin = getdate() " +
                        "select @FechaIni = d_inicio_tem from t_temporada where c_activo_tem  = 1 " +
                        "if @FechaIni is null  begin set @FechaIni = dateadd(mm, -2, @FechaFin) end " +
                        "exec sp_frupa_inventario @FechaIni, @FechaFin")
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
            
            self.stdout.write("🟡 Limpiando datos anteriores en Supabase...")
            supabase.table("conc_eye_inventario").delete().neq("c_codigo_tem", "00000000").execute()
            self.stdout.write("🟡 Insertando nuevos datos...")
            supabase.table("conc_eye_inventario").insert(datos_a_subir).execute()

            self.stdout.write(self.style.SUCCESS(f"🟢 ¡Sincronización completada! Registros: {len(datos_a_subir)}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"🔴 Error: {e}"))

