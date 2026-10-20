from django.db import models
from django.contrib.auth.models import Permission

class ModuloSistema(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Módulo") # Ej: "Recursos Humanos", "Tablas Dinámicas"
    slug = models.SlugField(max_length=50, unique=True, help_text="Identificador único en URL, ej: rh, reportes, seguridad")
    orden = models.IntegerField(default=1, verbose_name="Orden de Aparición")
    activo = models.BooleanField(default=True, verbose_name="¿Módulo Activo?")

    class Meta:
        db_table = 'core_modulo_sistema'
        verbose_name = "Módulo del Sistema"
        verbose_name_plural = "Módulos del Sistema"
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class OpcionModulo(models.Model):
    modulo = models.ForeignKey(
        ModuloSistema, 
        on_delete=models.CASCADE, 
        related_name='opciones',
        verbose_name="Módulo Perteneciente"
    )
    titulo = models.CharField(max_length=100, verbose_name="Título del Menú") # Ej: "Empleados", "Mi Panel de Evaluación"
    link = models.CharField(max_length=255, verbose_name="Ruta / Enlace (URL)") # Ej: "/admin/rh/empleado/"
    icono = models.CharField(max_length=50, default="link", verbose_name="Icono (Material Icon)") # Ej: "people", "badge"
    orden = models.IntegerField(default=1, verbose_name="Orden en el Menú")
    
    # 🌟 VINCULACIÓN CON EL MOTOR DE PERMISOS DE DJANGO
    permiso_requerido = models.ForeignKey(
        Permission, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Permiso Requerido",
        help_text="Si se deja vacío, cualquier usuario autenticado podrá ver esta opción."
    )
    solo_superusuario = models.BooleanField(
        default=False, 
        verbose_name="¿Exclusivo para Superusuarios?"
    )

    class Meta:
        db_table = 'core_opcion_modulo'
        verbose_name = "Opción de Módulo"
        verbose_name_plural = "Opciones de Módulos"
        ordering = ['modulo', 'orden', 'titulo']

    def __str__(self):
        return f"{self.modulo.nombre} -> {self.titulo}"