"""
Las competencias calificadas con 0 son "NA" (no aplica para el puesto): sí están contestadas.
Recalcula el avance de las entregas contando el NA; las que ya estaban completas se quedan así.
"""
from django.db import migrations


def recalcular(apps, schema_editor):
    from django.utils import timezone
    Entrega = apps.get_model('rh', 'EvaluacionEntrega')
    EvaluacionDet = apps.get_model('rh', 'EvaluacionDet')
    Competencia = apps.get_model('rh', 'Competencia')
    Asignada = apps.get_model('rh', 'EmpleadoCompetenciaAsignada')
    generales = set(Competencia.objects.filter(id_clasificacion__tipo='G').values_list('id_competencia', flat=True))
    for e in Entrega.objects.select_related('id_empleado'):
        emp = e.id_empleado
        if e.tipo == 'E' and not emp.se_evalua:
            requeridas = set()
        else:
            requeridas = generales | set(Asignada.objects.filter(id_empleado=emp).values_list('id_competencia_id', flat=True))
        hechas = set(EvaluacionDet.objects.filter(id_evaluacion_id=e.id_evaluacion_id, id_empleado=emp, tipo=e.tipo,
                                                  calificacion__isnull=False).values_list('id_competencia_id', flat=True))
        e.contestadas = len(requeridas & hechas)
        e.total = len(requeridas)
        if not e.completa and requeridas and requeridas <= hechas:
            e.completa = True
            e.fecha_completa = timezone.now()
        e.save()


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0037_evaluacion_entrega'),
    ]

    operations = [
        migrations.RunPython(recalcular, migrations.RunPython.noop),
    ]
