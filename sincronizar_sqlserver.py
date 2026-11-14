"""
Sube información de SQL Server a Supabase (Postgres) y deja registro en rep_bitacora_sincronizacion.

No depende de Django: corre en cualquier equipo con Python 3.10+ y el driver ODBC "SQL Server".
    python sincronizar_sqlserver.py 1      (1 = Inventario, 2 = Detalle de Ventas, 3 = Proceso de maquila, 4 = Cajas por empleado, 5 = Pallets,
                                            6 = Catálogos de RH desde nómina)
    python sincronizar_sqlserver.py 6 --simular     (hace todo y lo deshace al final: solo muestra el resumen)

Lee del .env (misma carpeta): SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD y
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT (la conexión a Supabase del portal).
El proceso 6 usa además NOM_SQL_SERVER, NOM_SQL_USER, NOM_SQL_PASSWORD y NOM_EMPRESAS (ver abajo).
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
    Proceso de maquila de la temporada activa (recepción contra t_palet, un renglón por estiba + producto +
    etiqueta). La consulta vive en el procedimiento dbo.sp_frupa_proceso_maquila (sql/sp_frupa_proceso_maquila.sql),
    que también usa Fruverpack (frmTableroMaquila): así la web y el escritorio dan los mismos números.
    """
    return "SET NOCOUNT ON; EXEC dbo.sp_frupa_proceso_maquila"


def consulta_cajas_empleado():
    """
    Cajas por empleado de la temporada activa: cajas etiquetadas por empacador por día, con charola y bolsa.
    La consulta vive en dbo.sp_frupa_cajas_empleado (sql/sp_frupa_cajas_empleado.sql), que también usa Fruverpack.
    """
    return "SET NOCOUNT ON; EXEC dbo.sp_frupa_cajas_empleado"


def consulta_pallets():
    """Pallets empacados de la temporada activa (t_palet), un renglón por pallet y sección. Vive en dbo.sp_frupa_pallets."""
    return "SET NOCOUNT ON; EXEC dbo.sp_frupa_pallets"


# proceso -> (nombre, función que arma la consulta, tabla destino, qué se borra antes de insertar):
#   None          = toda la tabla
#   "columna"     = las fechas del año en curso en esa columna
#   ("columna",)  = solo los valores de esa columna que trae la consulta (p. ej. la temporada activa)
PROCESOS = {
    1: ("Inventario", consulta_inventario, "rep_eye_inventario", None),
    2: ("Detalle de Ventas", consulta_ventas, "rep_detalleventas", "FechaFac"),
    3: ("Proceso de maquila", consulta_maquila, "rep_proceso_maquila", ("temporada",)),
    4: ("Cajas por empleado", consulta_cajas_empleado, "rep_cajas_empleado", ("temporada",)),
    5: ("Pallets", consulta_pallets, "rep_pallets", ("temporada",)),
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


# ---------------------------------------------------------------------------------------------------------
#   Proceso 6: catálogos de RH desde el sistema de nómina (otra base de SQL Server, una por empresa)
# ---------------------------------------------------------------------------------------------------------
# .env:
#   NOM_SQL_SERVER, NOM_SQL_USER, NOM_SQL_PASSWORD   (si faltan, se usan SQL_SERVER / SQL_USER / SQL_PASSWORD)
#   NOM_EMPRESAS = FRUSA:base_de_frusa;FRUPA:base_de_frupa      (empresa del portal : base de nómina)
#
# Solo se escriben los campos que vienen de nómina. Lo que se captura en el portal (jefe inmediato, encargado,
# ¿se evalúa?, debe cambiar password, usuario y competencias) nunca se toca. No se borra nada: las bajas
# llegan de nómina con su estado.

CONSULTA_DEPARTAMENTOS = "SELECT iddepartamento, descripcion FROM dbo.nom10003"
CONSULTA_PUESTOS = "SELECT idpuesto, descripcion FROM dbo.nom10006"
CONSULTA_EMPLEADOS = ("SELECT idempleado, iddepartamento, idpuesto, nombrelargo, estadoempleado, fechaalta, CorreoElectronico "
                      "FROM dbo.nom10001")


def empresas_nomina():
    """{'FRUSA': 'base', ...} según NOM_EMPRESAS."""
    resultado = {}
    for parte in (os.getenv('NOM_EMPRESAS') or '').replace(',', ';').split(';'):
        if ':' in parte:
            empresa, base = (x.strip() for x in parte.split(':', 1))
            if empresa and base:
                resultado[empresa] = base
    return resultado


def conectar_nomina(base):
    return pyodbc.connect(
        "DRIVER={SQL Server};"
        f"SERVER={os.getenv('NOM_SQL_SERVER') or os.getenv('SQL_SERVER', 'localhost')};"
        f"DATABASE={base};"
        f"UID={_valor_odbc(os.getenv('NOM_SQL_USER') or os.getenv('SQL_USER'))};"
        f"PWD={_valor_odbc(os.getenv('NOM_SQL_PASSWORD') or os.getenv('SQL_PASSWORD'))}"
    )


def _valor_odbc(valor):
    # Entre llaves para que una contraseña con ; = { } no rompa la cadena de conexión
    return '{' + str(valor or '').replace('}', '}}') + '}'


def _texto(valor):
    return str(valor).strip() if valor is not None else ''


def _estado(valor):
    # Nómina: A = alta, R = reingreso (activo), B = baja
    return 'B' if _texto(valor).upper().startswith('B') else 'A'


def _fecha(valor):
    if valor is None:
        return None
    return valor.date() if hasattr(valor, 'date') else valor


def _upsert_catalogo(cur, tabla, campo_id, empresa, filas):
    """Inserta o actualiza la descripción; devuelve ({número: id del portal}, insertados, actualizados)."""
    insertados = actualizados = 0
    for numero, descripcion in filas:
        cur.execute(
            f'INSERT INTO public.{tabla} (empresa, {campo_id}, descripcion) VALUES (%s, %s, %s) '
            f'ON CONFLICT (empresa, {campo_id}) DO UPDATE SET descripcion = EXCLUDED.descripcion '
            f'WHERE public.{tabla}.descripcion IS DISTINCT FROM EXCLUDED.descripcion '
            f'RETURNING (xmax = 0)',
            [empresa, int(numero), _texto(descripcion) or f'SIN DESCRIPCIÓN {numero}'],
        )
        r = cur.fetchone()
        if r is not None:
            if r[0]:
                insertados += 1
            else:
                actualizados += 1
    cur.execute(f'SELECT {campo_id}, id FROM public.{tabla} WHERE empresa = %s', [empresa])
    return dict(cur.fetchall()), insertados, actualizados


def sincronizar_catalogos_rh(pg, salida=print):
    """Departamentos, puestos y empleados de cada empresa de NOM_EMPRESAS. Devuelve (registros, resumen)."""
    empresas = empresas_nomina()
    if not empresas:
        raise ValueError("Falta NOM_EMPRESAS en el .env (ej. NOM_EMPRESAS=FRUSA:base_frusa;FRUPA:base_frupa).")
    total, resumen = 0, []
    for empresa, base in empresas.items():
        salida(f"[Catálogos de RH] {empresa}: consultando {base}...")
        sql = conectar_nomina(base)
        try:
            cur_sql = sql.cursor()
            departamentos = cur_sql.execute(CONSULTA_DEPARTAMENTOS).fetchall()
            puestos = cur_sql.execute(CONSULTA_PUESTOS).fetchall()
            empleados = cur_sql.execute(CONSULTA_EMPLEADOS).fetchall()
        finally:
            sql.close()

        with pg.cursor() as cur:
            deptos, dep_ins, dep_act = _upsert_catalogo(cur, 'rh_departamento', 'id_departamento', empresa, departamentos)
            ptos, pto_ins, pto_act = _upsert_catalogo(cur, 'rh_puesto', 'id_puesto', empresa, puestos)

            emp_ins = emp_act = 0
            sin_puesto = []
            for idemp, iddep, idpto, nombre, estado, fechaalta, correo in empleados:
                puesto = ptos.get(int(idpto)) if idpto is not None else None
                if puesto is None:
                    # El puesto es obligatorio en el portal
                    sin_puesto.append(f"{idemp} {_texto(nombre)}")
                    continue
                valores = [empresa, int(idemp), _texto(nombre), deptos.get(int(iddep)) if iddep is not None else None,
                           puesto, _estado(estado), _fecha(fechaalta), _texto(correo) or None]
                cur.execute(
                    'INSERT INTO public.rh_empleado (empresa, id_empleado, nombre_largo, id_departamento, id_puesto, '
                    '    estado_empleado, fechaalta, "CorreoElectronico", es_jefe_departamento, se_evalua, debe_cambiar_password) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false, false, true) '
                    'ON CONFLICT (empresa, id_empleado) DO UPDATE SET '
                    '    nombre_largo = EXCLUDED.nombre_largo, id_departamento = EXCLUDED.id_departamento, '
                    '    id_puesto = EXCLUDED.id_puesto, estado_empleado = EXCLUDED.estado_empleado, '
                    '    fechaalta = EXCLUDED.fechaalta, "CorreoElectronico" = EXCLUDED."CorreoElectronico" '
                    'WHERE (public.rh_empleado.nombre_largo, public.rh_empleado.id_departamento, public.rh_empleado.id_puesto, '
                    '       public.rh_empleado.estado_empleado, public.rh_empleado.fechaalta, public.rh_empleado."CorreoElectronico") '
                    '  IS DISTINCT FROM (EXCLUDED.nombre_largo, EXCLUDED.id_departamento, EXCLUDED.id_puesto, '
                    '       EXCLUDED.estado_empleado, EXCLUDED.fechaalta, EXCLUDED."CorreoElectronico") '
                    'RETURNING (xmax = 0)',
                    valores,
                )
                r = cur.fetchone()
                if r is not None:
                    if r[0]:
                        emp_ins += 1
                    else:
                        emp_act += 1

        linea = (f"{empresa}: departamentos {len(departamentos)} ({dep_ins} nuevos, {dep_act} cambiados), "
                 f"puestos {len(puestos)} ({pto_ins} nuevos, {pto_act} cambiados), "
                 f"empleados {len(empleados)} ({emp_ins} nuevos, {emp_act} cambiados)")
        if sin_puesto:
            linea += f". Sin puesto válido, no se subieron ({len(sin_puesto)}): " + ", ".join(sin_puesto[:20])
        salida(f"[Catálogos de RH] {linea}")
        resumen.append(linea)
        total += len(departamentos) + len(puestos) + len(empleados) - len(sin_puesto)
    return total, "\n".join(resumen)


# Procesos que no son "consulta y reemplazo de tabla": reciben la conexión a Supabase (en una transacción)
ESPECIALES = {6: ("Catálogos de RH", "rh_empleado, rh_puesto, rh_departamento", sincronizar_catalogos_rh)}


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


def sincronizar_especial(proceso, salida=print, simular=False):
    nombre, tablas, funcion = ESPECIALES[proceso]
    bitacora = None if simular else Bitacora(proceso, nombre, tablas)
    try:
        pg = conectar_supabase()
        try:
            with pg:   # una sola transacción: si algo falla no queda nada a medias
                registros, resumen = funcion(pg, salida)
                if simular:
                    pg.rollback()
                    salida(f"[{nombre}] SIMULACIÓN: no se guardó nada.")
        finally:
            pg.close()
    except Exception as error:
        if bitacora:
            bitacora.cerrar('error', mensaje=str(error))
        raise
    if bitacora:
        bitacora.cerrar('correcto', registros=registros, mensaje=resumen)
    salida(f"[{nombre}] Sincronización completada: {registros} registros.")
    return registros


def sincronizar(proceso, salida=print, simular=False):
    """Ejecuta un proceso completo. Devuelve los registros subidos; lanza la excepción si falla."""
    if proceso in ESPECIALES:
        return sincronizar_especial(proceso, salida, simular)
    if proceso not in PROCESOS:
        raise ValueError(f"Opción inválida: {proceso}. Usa {', '.join(map(str, list(PROCESOS) + list(ESPECIALES)))}.")
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
        sincronizar(opcion, simular='--simular' in sys.argv)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
