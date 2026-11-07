"""
Proceso de maquila: lo recibido (cajas_recibidas de t_recepciondet) son pallets. Solo cambia el nombre visible
de esos campos en el formato base de la tabla dinámica; se respeta el resto de la configuración.
"""
from django.db import migrations

SLUG = 'proceso-maquila'
TITULOS = {'CajasRecibidas': ('Cajas recibidas', 'Pallets recibidos'),
           'PromedioPorCaja': ('Prom. kg por caja recibida', 'Prom. kg por pallet')}


def renombrar(apps, schema_editor, nuevo=True):
    Pivot_Dinamico = apps.get_model('reportes', 'Pivot_Dinamico')
    reporte = Pivot_Dinamico.objects.filter(slug=SLUG).first()
    if not reporte or not isinstance(reporte.configuracion_pivot, dict):
        return
    for campo in reporte.configuracion_pivot.get('fields', []):
        clave = campo.get('name') or campo.get('dataField')
        if clave in TITULOS:
            campo['caption'] = TITULOS[clave][1 if nuevo else 0]
    reporte.save(update_fields=['configuracion_pivot'])


def regresar(apps, schema_editor):
    renombrar(apps, schema_editor, nuevo=False)


class Migration(migrations.Migration):

    dependencies = [
        ('reportes', '0012_menu_tablero_maquila'),
    ]

    operations = [
        migrations.RunPython(renombrar, regresar),
    ]
