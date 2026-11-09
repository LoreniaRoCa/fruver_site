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
            ("ver_proceso_maquila_pivot", "Puede ver el reporte: Proceso de maquila"),
            ("ver_cajas_empleado_pivot", "Puede ver el reporte: Cajas por empleado"),
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


class ClaveExcel(models.Model):
    """
    Clave personal con la que Excel (Power Query) consulta los reportes. Excel la pide la primera vez
    (autenticación "Básica": usuario del portal + esta clave) y la guarda en la computadora, no en el archivo.
    Solo se guarda el SHA-256 de la clave; el usuario la ve una sola vez al generarla.
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='claves_excel')
    nombre = models.CharField(max_length=100, verbose_name="Equipo o descripción", help_text="Ej. Laptop oficina")
    prefijo = models.CharField(max_length=12, verbose_name="Inicio de la clave", help_text="Para reconocerla sin mostrarla completa")
    clave_hash = models.CharField(max_length=64, unique=True, editable=False)
    activa = models.BooleanField(default=True, verbose_name="¿Activa?")
    vence = models.DateField(null=True, blank=True, verbose_name="Vence", help_text="Vacío = no vence")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Creada")
    ultimo_uso = models.DateTimeField(null=True, blank=True, verbose_name="Último uso")

    class Meta:
        db_table = 'rep_clave_excel'
        verbose_name = "Clave de Excel"
        verbose_name_plural = "Claves de Excel"
        ordering = ['usuario__username', '-fecha_creacion']

    def __str__(self):
        return f"{self.usuario} - {self.nombre} ({self.prefijo}…)"


class BitacoraConsultaExcel(models.Model):
    """Cada vez que un Excel actualiza los datos de un reporte (correcta, rechazada o con error)."""
    CORRECTO = 'correcto'
    DENEGADO = 'denegado'
    ERROR = 'error'
    ESTATUS = [(CORRECTO, 'Correcto'), (DENEGADO, 'Denegado'), (ERROR, 'Error')]

    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    clave = models.ForeignKey(ClaveExcel, null=True, blank=True, on_delete=models.SET_NULL, related_name='consultas')
    reporte = models.ForeignKey(Pivot_Dinamico, null=True, blank=True, on_delete=models.SET_NULL, related_name='consultas_excel')
    empresa = models.CharField(max_length=20, blank=True, default='')
    parametros = models.JSONField(default=dict, blank=True, verbose_name="Parámetros")
    version_plantilla = models.CharField(max_length=20, blank=True, default='', verbose_name="Versión de la plantilla")
    filas = models.PositiveIntegerField(default=0)
    duracion_ms = models.PositiveIntegerField(default=0, verbose_name="Duración (ms)")
    estatus = models.CharField(max_length=20, choices=ESTATUS)
    mensaje = models.TextField(blank=True, default='')
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")

    class Meta:
        db_table = 'rep_bitacora_consulta_excel'
        verbose_name = "Consulta desde Excel"
        verbose_name_plural = "Bitácora de consultas desde Excel"
        ordering = ['-fecha']
        indexes = [models.Index(fields=['reporte', '-fecha'], name='rep_bitexcel_rep_fecha_idx')]

    def __str__(self):
        return f"{self.usuario} {self.reporte} {self.fecha:%d/%m/%Y %H:%M} ({self.get_estatus_display()})"
