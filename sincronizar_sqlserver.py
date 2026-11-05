"""
Sube información de SQL Server a Supabase (Postgres) y deja registro en rep_bitacora_sincronizacion.

No depende de Django: corre en cualquier equipo con Python 3.10+ y el driver ODBC "SQL Server".
    python sincronizar_sqlserver.py 1      (1 = Inventario, 2 = Detalle de Ventas, 3 = Proceso de maquila)

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


def consulta_maquila():
    """
    Proceso de maquila de la temporada activa: lo que entregó el productor (recepción) contra lo que salió
    del empaque (t_palet). Un renglón por estiba + producto + etiqueta.
    - resumen: "estiba | promedio por caja | cajas | kilos recibidos", para agrupar en la tabla dinámica.
    - kilos_recibidos y cajas_recibidas solo vienen en el primer renglón de cada estiba (en los demás 0),
      para sumarlos por lote, dueño o variedad sin duplicar; el "% del recibido" divide cada celda entre
      los kilos recibidos del total de su renglón.
    """
    return """
SET NOCOUNT ON;
DECLARE @temporada CHAR(2), @empresa CHAR(2) = '00';
SELECT TOP 1 @temporada = c_codigo_tem FROM dbo.t_temporada WITH (NOLOCK) WHERE c_activo_tem = '1' ORDER BY c_codigo_tem DESC;

WITH Pal AS (
    SELECT  pal.c_codigo_tem, pal.c_codigo_sel, pal.c_codigo_pro, pal.c_codigo_eti, pal.c_codigo_env,
            n_bulxpa_pal = SUM(pal.n_bulxpa_pal)
    FROM    dbo.t_palet pal WITH (NOLOCK)
    WHERE   pal.c_codigo_tem = @temporada AND pal.c_codigo_emp = @empresa
    GROUP BY pal.c_codigo_tem, pal.c_codigo_sel, pal.c_codigo_pro, pal.c_codigo_eti, pal.c_codigo_env
),
Cant AS (
    SELECT  red.c_codigo_tem, red.c_codigo_sel,
            Kilos = SUM(ISNULL(red.n_kilos_red, 0.0)),
            Cajas = SUM(ISNULL(red.n_cajascorte_red, 0))
    FROM    dbo.t_recepciondet red WITH (NOLOCK)
    WHERE   red.c_codigo_tem = @temporada
    GROUP BY red.c_codigo_tem, red.c_codigo_sel
),
Est AS (
    SELECT  sel.c_codigo_tem, sel.c_codigo_sel,
            fecha    = CAST(sel.d_fecha_sel AS DATE),
            lote     = RTRIM(lot.c_codigo_lot) + ' ' + lot.v_nombre_lot,
            huerta   = hue.v_nombre_hue,
            dueno    =  case when isnull(dno.v_pagara_dno, '')='' then v_nombre_dno else dno.v_pagara_dno end,
            cultivo  = cul.v_nombre_cul,
            variedad = vari.v_nombre_var,
            kilos_recibidos = Cant.Kilos,
            cajas_recibidas = Cant.Cajas,
            resumen  = sel.c_codigo_sel
                       + ' | ' + FORMAT(Cant.Kilos / NULLIF(Cant.Cajas, 0), 'N2', 'en-US') + ' kg/caja'
                       + ' | ' + FORMAT(Cant.Cajas, 'N0', 'en-US') + ' cajas'
                       + ' | ' + FORMAT(Cant.Kilos, 'N2', 'en-US') + ' kg'
    FROM    dbo.t_seleccion sel WITH (NOLOCK)
            INNER JOIN Cant ON Cant.c_codigo_sel = sel.c_codigo_sel AND Cant.c_codigo_tem = sel.c_codigo_tem
            INNER JOIN dbo.t_lote lot WITH (NOLOCK) ON lot.c_codigo_lot = sel.c_codigo_lot AND lot.c_codigo_tem = sel.c_codigo_tem
            INNER JOIN dbo.t_cultivo cul WITH (NOLOCK) ON cul.c_codigo_cul = lot.c_codigo_cul
            INNER JOIN dbo.cosvariedad vari WITH (NOLOCK) ON vari.c_codigo_var = lot.c_codigo_var
            LEFT  JOIN dbo.t_huerto hue WITH (NOLOCK) ON hue.c_codigo_hue = lot.c_codigo_hue
            LEFT  JOIN dbo.t_duenio dno WITH (NOLOCK) ON dno.c_codigo_dno = hue.c_codigo_dno
    WHERE   sel.c_codigo_tem = @temporada
),
Det AS (
    SELECT  Est.c_codigo_sel,
            -- Envase 03 (KILOGRAMOS / bins) = mermas y subproductos; lo demás es empaque
            tipo         = CASE WHEN Pal.c_codigo_env = '03' THEN 'Mermas y subproductos' ELSE 'Empaque' END,
            presentacion = CASE WHEN Pal.c_codigo_env = '03'                 THEN tam.v_nombre_tam
                                WHEN isnull(cal.v_nombre_prc, tam.v_nombre_tam) LIKE 'CHAROLA SELECTA%'  THEN 'Selecta charola'
                                WHEN isnull(cal.v_nombre_prc, tam.v_nombre_tam) LIKE 'CHAROLA COMERCIAL%' THEN 'Comercial charola'
                                WHEN isnull(cal.v_nombre_prc, tam.v_nombre_tam) LIKE 'BOLSA%'             THEN 'Bolsa'
                                ELSE isnull(cal.v_nombre_prc, tam.v_nombre_tam) END,
            calidad  = isnull(cal.v_nombre_prc, tam.v_nombre_tam),
            envase   = env.v_nombre_env,
            etiqueta = RTRIM(eti.v_nombre_eti),
            tamano   = tam.v_nombre_tam,
            producto = pro.v_nombre_pro,
            cajas    = Pal.n_bulxpa_pal,
            kilos    = pro.n_pesbul_pro * Pal.n_bulxpa_pal,  -- peso promedio del producto
            -- Lo recibido solo en el primer renglón de la estiba
            primero  = ROW_NUMBER() OVER (PARTITION BY Est.c_codigo_sel ORDER BY Pal.c_codigo_env, pro.c_codigo_pro, Pal.c_codigo_eti)
    FROM    Pal
            INNER JOIN Est ON Est.c_codigo_sel = Pal.c_codigo_sel AND Est.c_codigo_tem = Pal.c_codigo_tem
            INNER JOIN dbo.t_producto pro WITH (NOLOCK) ON pro.c_codigo_pro = Pal.c_codigo_pro
            LEFT OUTER JOIN dbo.t_producto_calidad cal WITH (NOLOCK) ON cal.c_codigo_prc = pro.c_codigo_prc
            INNER JOIN dbo.t_tamanio tam WITH (NOLOCK) ON tam.c_codigo_tam = pro.c_codigo_tam
            INNER JOIN dbo.t_etiqueta eti WITH (NOLOCK) ON eti.c_codigo_eti = Pal.c_codigo_eti
            INNER JOIN dbo.t_envase env WITH (NOLOCK) ON env.c_codigo_env = Pal.c_codigo_env
)
SELECT  temporada = Est.c_codigo_tem, estiba = Est.c_codigo_sel, Est.fecha, Est.lote, Est.huerta, Est.dueno,
        Est.cultivo, Est.variedad, Est.resumen, Det.tipo, Det.presentacion, Det.calidad, Det.envase, Det.etiqueta,
        Det.tamano, Det.producto, Det.cajas, Det.kilos,
        kilos_recibidos = CASE WHEN Det.primero = 1 THEN Est.kilos_recibidos ELSE 0 END,
        cajas_recibidas = CASE WHEN Det.primero = 1 THEN Est.cajas_recibidas ELSE 0 END
FROM    Det
        INNER JOIN Est ON Est.c_codigo_sel = Det.c_codigo_sel
ORDER BY Est.c_codigo_sel, Det.tipo, Det.presentacion, Det.tamano;
"""


# proceso -> (nombre, función que arma la consulta, tabla destino, qué se borra antes de insertar):
#   None          = toda la tabla
#   "columna"     = las fechas del año en curso en esa columna
#   ("columna",)  = solo los valores de esa columna que trae la consulta (p. ej. la temporada activa)
PROCESOS = {
    1: ("Inventario", consulta_inventario, "rep_eye_inventario", None),
    2: ("Detalle de Ventas", consulta_ventas, "rep_detalleventas", "FechaFac"),
    3: ("Proceso de maquila", consulta_maquila, "rep_proceso_maquila", ("temporada",)),
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
        raise ValueError(f"Opción inválida: {proceso}. Usa {', '.join(map(str, PROCESOS))}.")
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
                if isinstance(campo_fecha, tuple):
                    posicion = columnas.index(campo_fecha[0])
                    valores = sorted({f[posicion] for f in filas})
                    cur.execute(f'DELETE FROM public."{tabla}" WHERE "{campo_fecha[0]}" = ANY(%s)', [valores])
                elif campo_fecha:
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
