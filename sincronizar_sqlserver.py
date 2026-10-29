"""
Sube información de SQL Server a Supabase (Postgres) y deja registro en rep_bitacora_sincronizacion.

No depende de Django: corre en cualquier equipo con Python 3.10+ y el driver ODBC "SQL Server".
    python sincronizar_sqlserver.py 1      (1 = Inventario, 2 = Detalle de Ventas)

Lee del .env (misma carpeta): SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD y
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT (la conexión a Supabase del portal).
El portal también lo usa desde `python manage.py subirsqlserver --tabla N`.
"""
import os
import socket
import sys
from datetime import date
from pathlib import Path

import psycopg2
import pyodbc
from dotenv import load_dotenv
from psycopg2.extras import execute_values

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env', override=True)


def consulta_inventario():
    return (
        "declare @FechaIni Datetime, @FechaFin Datetime "
        "select @FechaFin = getdate() "
        "select @FechaIni = d_inicio_tem from t_temporada where c_activo_tem = 1 "
        "if @FechaIni is null begin set @FechaIni = dateadd(mm, -2, @FechaFin) end "
        "exec sp_frupa_inventario @FechaIni, @FechaFin"
    )


def consulta_ventas():
    # Año en curso completo (antes estaba fijo en 2026-01-01 / 2026-12-31)
    anio = date.today().year
    return f"exec AgroSmart_FRUSA.dbo.sp_fru_ventas_pivot '{anio}0101', '{anio}1231', 1"


# proceso -> (nombre, función que arma la consulta, tabla destino, columna de fecha para borrar solo el rango)
PROCESOS = {
    1: ("Inventario", consulta_inventario, "rep_eye_inventario", None),
    2: ("Detalle de Ventas", consulta_ventas, "rep_detalleventas", "FechaFac"),
}


def conectar_supabase():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT") or 6543),
        connect_timeout=30,
    )


def conectar_sqlserver():
    return pyodbc.connect(
        "DRIVER={SQL Server};"
        f"SERVER={os.getenv('SQL_SERVER', 'localhost')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USER')};"
        f"PWD={os.getenv('SQL_PASSWORD')}"
    )


class Bitacora:
    """Una fila en rep_bitacora_sincronizacion por ejecución (se ve en el admin del portal)."""

    def __init__(self, proceso, nombre, tabla):
        # Conexión propia en autocommit: el registro queda aunque la carga se deshaga por error
        self.conn = conectar_supabase()
        self.conn.autocommit = True
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO rep_bitacora_sincronizacion "
                "(proceso, nombre_proceso, tabla_destino, equipo, fecha_inicio, estatus, registros, mensaje) "
                "VALUES (%s, %s, %s, %s, now(), 'en_proceso', 0, '') RETURNING id",
                [proceso, nombre, tabla, socket.gethostname()[:100]],
            )
            self.id = cur.fetchone()[0]

    def cerrar(self, estatus, registros=0, mensaje=''):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE rep_bitacora_sincronizacion SET estatus = %s, registros = %s, mensaje = %s, fecha_fin = now() "
                "WHERE id = %s",
                [estatus, registros, mensaje[:2000], self.id],
            )
        self.conn.close()


def sincronizar(proceso, salida=print):
    """Ejecuta un proceso completo. Devuelve los registros subidos; lanza la excepción si falla."""
    if proceso not in PROCESOS:
        raise ValueError(f"Opción inválida: {proceso}. Usa 1 o 2.")
    nombre, armar_consulta, tabla, campo_fecha = PROCESOS[proceso]

    bitacora = Bitacora(proceso, nombre, tabla)
    try:
        salida(f"[{nombre}] Consultando SQL Server...")
        sql_conn = conectar_sqlserver()
        try:
            cursor = sql_conn.cursor()
            consulta = armar_consulta()
            cursor.execute(consulta)
            filas = cursor.fetchall()
            columnas = [c[0] for c in cursor.description] if cursor.description else []
        finally:
            sql_conn.close()

        if not filas:
            salida(f"[{nombre}] No hay registros para sincronizar.")
            bitacora.cerrar('sin_datos', mensaje="No hay registros para sincronizar.")
            return 0

        salida(f"[{nombre}] Subiendo {len(filas)} registros a {tabla}...")
        lista_columnas = ", ".join(f'"{c}"' for c in columnas)
        pg = conectar_supabase()
        try:
            # Borrado e inserción en una sola transacción: si algo falla, la tabla queda como estaba
            with pg, pg.cursor() as cur:
                if campo_fecha:
                    anio = date.today().year
                    cur.execute(
                        f'DELETE FROM public."{tabla}" WHERE "{campo_fecha}"::date BETWEEN %s AND %s',
                        [date(anio, 1, 1), date(anio, 12, 31)],
                    )
                else:
                    cur.execute(f'TRUNCATE TABLE public."{tabla}" RESTART IDENTITY')
                execute_values(
                    cur,
                    f'INSERT INTO public."{tabla}" ({lista_columnas}) VALUES %s',
                    [tuple(f) for f in filas],
                    page_size=1000,
                )
        finally:
            pg.close()
    except Exception as error:
        bitacora.cerrar('error', mensaje=str(error))
        raise

    bitacora.cerrar('correcto', registros=len(filas))
    salida(f"[{nombre}] Sincronización completada: {len(filas)} registros en {tabla}.")
    return len(filas)


if __name__ == '__main__':
    try:
        opcion = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        sincronizar(opcion)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
