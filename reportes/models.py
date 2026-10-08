from django.db import models

# Create your models here.
class Pivot_Dinamico(models.Model):
    id_reporte = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150, verbose_name="Nombre del Reporte")
    slug = models.SlugField(max_length=150, unique=True, help_text="Identificador para la URL (ej. inventario-pivot)")
    query_sql = models.TextField(verbose_name="Consulta SQL (SELECT)", help_text="Escribe la consulta SQL pura que alimentará los datos.")
    configuracion_pivot = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name="Configuración DevExtreme (Campos, Filas, Columnas)",
        help_text="JSON con la estructura de fields de DevExtreme (row, column, data, area, format)."
    )
    icono = models.CharField(max_length=50, default="bar_chart", verbose_name="Icono de Material Symbols")
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")
    orden = models.IntegerField(default=0, verbose_name="Orden en el Menú")

    class Meta:
        verbose_name = "Reporte Dinámico"
        verbose_name_plural = "Reportes Dinámicos"
        ordering = ['orden', 'nombre']
        db_table = 'rep_pivot_dinamico'

    def __str__(self):
        return self.nombre