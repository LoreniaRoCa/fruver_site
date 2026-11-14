"""
Tablero de evaluaciones: la vista rh_vista_dashboard_departamentos contaba como "autoevaluado" a cualquier empleado
con calificaciones en la evaluación abierta, aunque fueran solo las de su jefe (tipo 'J'). Ahora la autoevaluación
solo cuenta las calificaciones del propio empleado (tipo 'E'), igual que el Consolidado de resultados.

La vista se había creado directo en Supabase; aquí queda su definición completa.
"""
from django.db import migrations

VISTA = """
CREATE OR REPLACE VIEW rh_vista_dashboard_departamentos AS
 SELECT dep.empresa,
    dep.departamento,
        CASE
            WHEN dep.jefe::text = ''::text THEN 'SIN ASIGNAR'::character varying
            ELSE dep.jefe
        END AS jefe,
    count(*) AS numempleados,
    sum(COALESCE(auto.numempleados, 0::bigint)) AS autoevaluados,
    sum(COALESCE(eval.numempleados, 0::bigint)) AS evaluados,
    sum(
        CASE
            WHEN auto.numempleados IS NOT NULL AND eval.numempleados IS NOT NULL THEN 1
            ELSE 0
        END) AS ambas
   FROM ( SELECT emp.id,
            emp.empresa,
            dep_1.descripcion AS departamento,
            COALESCE(jefe.nombre_largo, ''::character varying) AS jefe
           FROM rh_empleado emp
             JOIN rh_departamento dep_1 ON emp.id_departamento = dep_1.id
             LEFT JOIN rh_empleado jefe ON emp.id_jefe = jefe.id
          WHERE emp.se_evalua = true) dep
     LEFT JOIN ( SELECT emp.id,
            emp.empresa,
            dep_1.descripcion AS departamento,
            COALESCE(jefe.nombre_largo, ''::character varying) AS jefe,
            count(DISTINCT emp.id_empleado) AS numempleados
           FROM rh_empleado emp
             JOIN rh_departamento dep_1 ON emp.id_departamento = dep_1.id
             JOIN rh_evaluacion_det evald ON emp.id = evald.id_empleado AND evald.tipo::text = '{tipo_auto}'::text
             JOIN rh_evaluacion eval_1 ON evald.id_evaluacion::text = eval_1.id_evaluacion::text AND evald.empresa::text = eval_1.empresa::text AND eval_1.cerrada = false
             LEFT JOIN rh_empleado jefe ON emp.id_jefe = jefe.id
          WHERE emp.se_evalua = true
          GROUP BY emp.id, emp.empresa, dep_1.descripcion, (COALESCE(jefe.nombre_largo, ''::character varying))) auto ON dep.id = auto.id AND dep.departamento::text = auto.departamento::text AND dep.jefe::text = auto.jefe::text
     LEFT JOIN ( SELECT emp.id,
            emp.empresa,
            dep_1.descripcion AS departamento,
            COALESCE(jefe.nombre_largo, ''::character varying) AS jefe,
            count(DISTINCT emp.id_empleado) AS numempleados
           FROM rh_empleado emp
             JOIN rh_departamento dep_1 ON emp.id_departamento = dep_1.id
             JOIN rh_evaluacion_det evald ON emp.id = evald.id_empleado AND evald.tipo::text = 'J'::text
             JOIN rh_evaluacion eval_1 ON evald.id_evaluacion::text = eval_1.id_evaluacion::text AND evald.empresa::text = eval_1.empresa::text AND eval_1.cerrada = false
             LEFT JOIN rh_empleado jefe ON emp.id_jefe = jefe.id
          GROUP BY emp.id, emp.empresa, dep_1.descripcion, (COALESCE(jefe.nombre_largo, ''::character varying))) eval ON dep.id = eval.id AND dep.departamento::text = eval.departamento::text AND dep.jefe::text = eval.jefe::text
  GROUP BY dep.empresa, dep.departamento, (
        CASE
            WHEN dep.jefe::text = ''::text THEN 'SIN ASIGNAR'::character varying
            ELSE dep.jefe
        END)
  ORDER BY dep.departamento, (
        CASE
            WHEN dep.jefe::text = ''::text THEN 'SIN ASIGNAR'::character varying
            ELSE dep.jefe
        END);
"""

# Para regresar: la definición anterior (la autoevaluación tomaba cualquier tipo de calificación)
VISTA_ANTERIOR = VISTA.replace("evald.id_empleado AND evald.tipo::text = '{tipo_auto}'::text", "evald.id_empleado")


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0035_empresa_logo'),
    ]

    operations = [
        migrations.RunSQL(VISTA.replace('{tipo_auto}', 'E'), reverse_sql=VISTA_ANTERIOR),
    ]
