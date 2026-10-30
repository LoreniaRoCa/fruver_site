from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group, Permission

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
    grupo = models.CharField(max_length=100, default='General', blank=True, null=True)
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

class AccesoEmpresa(models.Model):
    """
    A qué empresas puede entrar un usuario y con qué grupos/permisos en cada una.
    Los grupos y permisos globales del usuario (los de Django) siguen valiendo en todas sus empresas;
    los de aquí se suman solo cuando la empresa activa de la sesión es esta.
    """
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accesos_empresa')
    empresa = models.ForeignKey('rh.Empresa', on_delete=models.CASCADE, related_name='accesos_usuario', db_column='empresa')
    grupos = models.ManyToManyField(Group, blank=True, related_name='accesos_empresa', verbose_name="Grupos (roles) en esta empresa")
    permisos = models.ManyToManyField(Permission, blank=True, related_name='accesos_empresa', verbose_name="Permisos adicionales en esta empresa")
    activo = models.BooleanField(default=True, verbose_name="¿Acceso activo?")

    class Meta:
        db_table = 'core_acceso_empresa'
        verbose_name = "Acceso por empresa"
        verbose_name_plural = "Accesos por empresa"
        unique_together = ('usuario', 'empresa')
        ordering = ['empresa']

    def __str__(self):
        return f"{self.usuario} -> {self.empresa_id}"
