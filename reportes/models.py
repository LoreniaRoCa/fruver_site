from django.db import models
from django.conf import settings

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
    
    # 🌟 MACROS DE FECHA EN LA CONSULTA BASE 🌟
    fecha_inicio_macro = models.CharField(max_length=20, default="-3m", verbose_name="Macro Fecha Inicial Default", help_text="Ejemplo: -3m, A1, M, Hoy")
    fecha_fin_macro = models.CharField(max_length=20, default="m", verbose_name="Macro Fecha Final Default", help_text="Ejemplo: m, a, Hoy")

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


class PlantillaPivotUsuario(models.Model):
    reporte_base = models.ForeignKey(
        Pivot_Dinamico, 
        on_delete=models.CASCADE, 
        related_name='plantillas'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='plantillas_pivot'
    )
    nombre_plantilla = models.CharField(max_length=150)
    configuracion_pivot = models.JSONField(
        help_text="Estado completo de DevExtreme obtenible con state()"
    )
    es_default = models.BooleanField(default=False)
    
    # 🌟 MACROS DE FECHA HEREDABLES (OPCIONALES EN PLANTILLA) 🌟
    fecha_inicio_macro = models.CharField(max_length=20, null=True, blank=True, verbose_name="Macro Fecha Inicial Personalizada")
    fecha_fin_macro = models.CharField(max_length=20, null=True, blank=True, verbose_name="Macro Fecha Final Personalizada")
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rep_plantilla_pivot_usuario'
        unique_together = ('reporte_base', 'usuario', 'nombre_plantilla')

    def __str__(self):
        return f"{self.nombre_plantilla} ({self.usuario})"