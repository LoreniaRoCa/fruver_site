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

# 🌟 NUEVO CAMPO: Identificador del permiso en auth_permission (ej. 'ver_inventario_pivot')
    permiso_codename = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Codename de Permiso Requerido",
        help_text="Codename registrado en auth_permission (ej. ver_inventario_pivot). Dejar vacío si es público."
    )
        
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")
    orden = models.IntegerField(default=0, verbose_name="Orden en el Menú")

    class Meta:
        verbose_name = "Reporte Dinámico"
        verbose_name_plural = "Reportes Dinámicos"
        ordering = ['orden', 'nombre']
        db_table = 'rep_pivot_dinamico'
        # 🌟 NUEVO: PERMISOS PARA LAS TABLAS DINÁMICAS / REPORTES
        permissions = [
            ("ver_inventario_pivot", "Puede ver el reporte: Inventario Pivot"),
            ("ver_ventas_pivot", "Puede ver el reporte: Ventas Pivot"),
            # Puedes ir agregando aquí permisos para otros reportes que crees a futuro
        ]

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

class BitacoraSincronizacion(models.Model):
    """Cada ejecución de `manage.py subirsqlserver` (SQL Server -> Supabase), una fila por corrida."""
    EN_PROCESO = 'en_proceso'
    CORRECTO = 'correcto'
    SIN_DATOS = 'sin_datos'
    ERROR = 'error'
    ESTATUS = [
        (EN_PROCESO, 'En proceso'),
        (CORRECTO, 'Correcto'),
        (SIN_DATOS, 'Sin datos'),
        (ERROR, 'Error'),
    ]

    proceso = models.PositiveSmallIntegerField(verbose_name="Proceso", help_text="Opción --tabla del comando")
    nombre_proceso = models.CharField(max_length=100, verbose_name="Nombre")
    tabla_destino = models.CharField(max_length=100, verbose_name="Tabla destino")
    equipo = models.CharField(max_length=100, blank=True, default='', verbose_name="Equipo que lo ejecutó")
    fecha_inicio = models.DateTimeField(verbose_name="Inicio")
    fecha_fin = models.DateTimeField(null=True, blank=True, verbose_name="Fin")
    estatus = models.CharField(max_length=20, choices=ESTATUS, default=EN_PROCESO)
    registros = models.PositiveIntegerField(default=0, verbose_name="Registros subidos")
    mensaje = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'rep_bitacora_sincronizacion'
        verbose_name = "Sincronización SQL Server"
        verbose_name_plural = "Bitácora de sincronización"
        ordering = ['-fecha_inicio']
        indexes = [models.Index(fields=['proceso', '-fecha_inicio'], name='rep_bitsinc_proc_fecha_idx')]

    def __str__(self):
        return f"{self.nombre_proceso} {self.fecha_inicio:%d/%m/%Y %H:%M} ({self.get_estatus_display()})"

    @property
    def duracion(self):
        if not self.fecha_fin:
            return None
        return self.fecha_fin - self.fecha_inicio
