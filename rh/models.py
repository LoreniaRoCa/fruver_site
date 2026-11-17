# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Empresa(models.Model):
    id_empresa = models.CharField(max_length=20, primary_key=True) # ej: 'FRUSA', 'EMPRESA_B'
    nombre = models.CharField(max_length=150) # ej: 'Fruta S.A. de C.V.'
    activa = models.BooleanField(default=True)
    # 🌟 Campo para el Logotipo
    logo = models.ImageField(
        upload_to='empresas/logos/', 
        null=True, 
        blank=True, 
        verbose_name="Logotipo de la Empresa",
        help_text="Suba la imagen del logotipo en formato PNG o JPG."
    )

    def __str__(self):
        return f"{self.id_empresa} - {self.nombre}"

class Competencia(models.Model):
    id_competencia = models.AutoField(primary_key=True)
# =========================================================================
    # EL TRUCO PARA EL NOMBRE DEL CAMPO: Agregamos verbose_name="Clasificación"
    # =========================================================================
    id_clasificacion = models.ForeignKey(
        'CompetenciaClasificacion', 
        models.DO_NOTHING, 
        db_column='id_clasificacion',
        verbose_name="Clasificación"  # <-- Así aparecerá en el formulario de agregar
    )
    descripcion = models.TextField()

    def __str__(self):
        return self.descripcion

    class Meta:
        managed = True
        db_table = 'rh_competencia'
        verbose_name = "Competencia"
        verbose_name_plural = "Competencias"


class CompetenciaClasificacion(models.Model):
    id_clasificacion = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=150)

    # 1. Definimos las opciones que verá el usuario
    OPCIONES_CLASIFICACION = [
        ('G', 'General'),
        ('E', 'Específica'),
    ]
    tipo = models.CharField(
        max_length=1,
        choices=OPCIONES_CLASIFICACION,   # Esto lo convierte en una lista desplegable
        default='E',              # Por defecto estará seleccionado "E"
        verbose_name="Tipo Competencia"
    )

# =========================================================================
    # EL TRUCO PARA EL MENÚ DESPLEGABLE: Muestra la descripción real
    # =========================================================================
    def __str__(self):
        return self.descripcion

    class Meta:
        managed = True
        db_table = 'rh_competencia_clasificacion'
        verbose_name = "Competencia clasificación"          
        verbose_name_plural = "Competencia Clasificaciones"   

class Departamento(models.Model):
    # 'id' es la nueva PK primaria manejada por Django
    id_departamento = models.IntegerField(verbose_name="ID Departamento (Local)")
    descripcion = models.CharField(max_length=150)
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )

    class Meta:
        managed = True
        db_table = 'rh_departamento'
        unique_together = ('empresa', 'id_departamento') # 🌟 Restricción multitenant
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['id_departamento']

    def __str__(self):
        return self.descripcion

class Empleado(models.Model):
    id_empleado = models.IntegerField(verbose_name="ID Empleado")

    # 2. El campo mágico: Relación uno a uno.
    # Un empleado pertenece a un usuario, un usuario pertenece a un empleado.
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL,  # Si borran el usuario, el empleado no se borra (queda en NULL)
        null=True, 
        blank=True, 
        verbose_name="Usuario de Sistema"
    )
    nombre_largo = models.CharField(max_length=255)
    
    # Un empleado pertenece a un departamento (puede omitirse temporalmente)
    id_departamento = models.ForeignKey(
        'Departamento', 
        models.SET_NULL, 
        db_column='id_departamento', 
        blank=True, 
        null=True,
        verbose_name="Departamento",
    )
    
    # AUTORELACIÓN: Un empleado reporta a otro empleado (su jefe directo)
    id_jefe = models.ForeignKey(
        'self', 
        models.SET_NULL, 
        db_column='id_jefe', 
        blank=True, 
        null=True,
        verbose_name="Jefe Inmediato",
    )
    
    id_puesto = models.ForeignKey(
        'Puesto', 
        models.DO_NOTHING, 
        db_column='id_puesto',
        verbose_name="Puesto",
    )
    
    # LA SOLUCIÓN: Saber si lidera el departamento al que está asignado
    es_jefe_departamento = models.BooleanField(
        default=False, 
        verbose_name="Encargado"
    )
    # 💡 Agrega esta línea para el nuevo campo de fecha de alta:
    fechaalta = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de Alta"
    )
    CorreoElectronico  = models.EmailField(
    blank=True, 
    null=True, 
    verbose_name="Correo Electrónico"
    )
    # 1. Definimos las opciones que verá el usuario
    OPCIONES_ESTADO = [
        ('A', 'Alta'),
        ('B', 'Baja'),
    ]
    estado_empleado = models.CharField(
        max_length=1,
        choices=OPCIONES_ESTADO,   # Esto lo convierte en una lista desplegable
        default='A',              # Por defecto estará seleccionado "Alta"
        verbose_name="Estado del Empleado"
    )
    se_evalua = models.BooleanField(
        default=False, 
        verbose_name="¿Se evalúa?"
    )    
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )
    debe_cambiar_password = models.BooleanField(
        default=True, 
        help_text="Si es True, obliga al usuario a cambiar su contraseña al iniciar sesión."
    )
    class Meta:
        managed = True
        db_table = 'rh_empleado'
        unique_together = ('empresa', 'id_empleado')
        ordering = ['id_empleado']

    def __str__(self):
        return self.nombre_largo

class Evaluacion(models.Model):
    id_evaluacion = models.CharField(primary_key=True, max_length=20)
    descripcion = models.CharField(max_length=255)
    fecha_inicial = models.DateField()
    fecha_final = models.DateField()
    # NUEVO CAMPO: Indica si el periodo de evaluación ya fue clausurado por el administrador
    cerrada = models.BooleanField(default=False, verbose_name="¿Evaluación Cerrada?")
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )
    class Meta:
        managed = True
        db_table = 'rh_evaluacion'
        # LOS CAMBIOS CLAVE:
        verbose_name = "Evaluación"          # Cómo se dice en singular
        verbose_name_plural = "Evaluaciones" # Cómo se mostrará en el menú de la izquierda

        # 🌟 AQUÍ AGREGAS LOS PERMISOS DE CADA VISTA DEL RECUADRO ROJO:
        permissions = [
            ("ver_panel_evaluacion", "Puede ver la vista: Mi Panel de Evaluación"),
            ("ver_consolidado_resultados", "Puede ver la vista: Consolidado Resultados"),
            ("ver_asignacion_competencias", "Puede ver la vista: Asignación de Competencias"),
        ]
class EvaluacionDet(models.Model):
    id_evaluacion = models.ForeignKey(Evaluacion, models.DO_NOTHING, db_column='id_evaluacion')
    id_competencia = models.ForeignKey(Competencia, models.DO_NOTHING, db_column='id_competencia')
    id_empleado = models.ForeignKey(Empleado, models.CASCADE, db_column='id_empleado')
    calificacion = models.IntegerField(blank=True, null=True)

    TIPO_EVALUADOR_CHOICES = [
        ('E', 'Empleado (Autoevaluación)'),
        ('J', 'Jefe (Evaluación a Colaborador)'),
    ]

    tipo = models.CharField(
        max_length=1,
        choices=TIPO_EVALUADOR_CHOICES,
        blank=False,
        null=False
    )
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )
    class Meta:
        unique_together = (('id_evaluacion', 'id_competencia', 'id_empleado', 'tipo'),)
        managed = True
        db_table = 'rh_evaluacion_det'


class Puesto(models.Model):
    # 'id' es la nueva PK primaria manejada por Django
    id_puesto = models.IntegerField(verbose_name="ID Puesto (Local)")
    descripcion = models.CharField(max_length=150)
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )

    class Meta:
        managed = True
        db_table = 'rh_puesto'
        unique_together = ('empresa', 'id_puesto') # 🌟 Restricción multitenant
        verbose_name = "Puesto"
        verbose_name_plural = "Puestos"
        ordering = ['id_puesto']

    def __str__(self):
        return self.descripcion

class EvaluacionComentario(models.Model):
    TIPO_BLOQUE_CHOICES = [
        ('G', 'Generales'),
        ('E', 'Específicas')
    ]
    TIPO_EVALUADOR_CHOICES = [
        ('E', 'Empleado (Autoevaluación)'),
        ('J', 'Jefe (Evaluación a Colaborador)')
    ]

    # Mapeo correcto hacia los nombres reales de la BD
    id_evaluacion = models.ForeignKey(
        Evaluacion, 
        on_delete=models.CASCADE, 
        db_column='id_evaluacion_id'  # <-- Debe incluir _id
    )
    id_empleado = models.ForeignKey(
        Empleado, 
        on_delete=models.CASCADE, 
        db_column='id_empleado_id'    # <-- Debe incluir _id
    )
    tipo_bloque = models.CharField(max_length=1, choices=TIPO_BLOQUE_CHOICES)
    tipo_evaluador = models.CharField(max_length=1, choices=TIPO_EVALUADOR_CHOICES)
    fortalezas = models.TextField(blank=True, null=True)
    areas_oportunidad = models.TextField(blank=True, null=True)
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )
    class Meta:
        db_table = 'rh_evaluacioncomentario'
        unique_together = ('id_evaluacion', 'id_empleado', 'tipo_bloque', 'tipo_evaluador')

    def __str__(self):
        return f"Comentarios {self.tipo_bloque} - {self.id_empleado.nombre_largo} ({self.tipo_evaluador})"

class ClasificacionPorPuesto(models.Model):
    id_puesto = models.ForeignKey(Puesto, on_delete=models.CASCADE, verbose_name="Puesto")
    id_clasificacion = models.ForeignKey(CompetenciaClasificacion, on_delete=models.CASCADE, verbose_name="Clasificación Asignada")
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )
    class Meta:
        verbose_name = "Clasificación por Puesto"
        verbose_name_plural = "Matriz: Clasificaciones por Puesto"
        unique_together = ('id_puesto', 'id_clasificacion') # Evita duplicados
        db_table = 'rh_clasificacionporpuesto'

# Tabla para asignar Clasificaciones o Competencias extra directas a un Empleado específico
class ClasificacionPorEmpleado(models.Model):
    id_empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, verbose_name="Empleado")
    id_clasificacion = models.ForeignKey(CompetenciaClasificacion, on_delete=models.CASCADE, verbose_name="Clasificación Extra")
    motivo = models.CharField(max_length=255, blank=True, null=True, help_text="Ej: Proyecto especial 2026")

    # Guardará el ID de la competencia creada automáticamente (Oculto para el usuario)
    competencia_exclusiva = models.ForeignKey(
        'Competencia', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        verbose_name="ID Competencia Exclusiva"
        
    )
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )
    class Meta:
        verbose_name = "Clasificación Especial por Empleado"
        verbose_name_plural = "Excepciones: Clasificaciones por Empleado"
        unique_together = ('id_empleado', 'id_clasificacion')
        db_table = 'rh_clasificacionporempleado'

class EmpleadoCompetenciaAsignada(models.Model):
    # 🌟 Se cambia db_column a 'id_empleado_id' y en id_competencia a 'id_competencia_id'
    id_empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='id_empleado_id', related_name='competencias_asignadas')
    id_competencia = models.ForeignKey('Competencia', on_delete=models.CASCADE, db_column='id_competencia_id')   
    fecha_asignacion = models.DateField(auto_now_add=True)
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='empresa'
    )
    class Meta:
        verbose_name = "Competencia Asignada a Empleado"
        verbose_name_plural = "Competencias Asignadas"
        unique_together = ('id_empleado', 'id_competencia') 
        db_table = 'rh_empleadocompetenciaasignada'

    # 🌟 AGREGAR ESTE MÉTODO SAVE:
    def save(self, *args, **kwargs):
        # Si la empresa no está asignada pero el empleado tiene empresa, la copia automáticamente
        if not self.empresa_id and self.id_empleado and self.id_empleado.empresa:
            self.empresa = self.id_empleado.empresa
        super().save(*args, **kwargs)        

class TokenAccesoEvaluacion(models.Model):
    id_token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 🌟 Se actualiza db_column a 'empleado_id'
    empleado = models.ForeignKey('Empleado', on_delete=models.CASCADE, db_column='empleado_id')
    creado_en = models.DateTimeField(auto_now_add=True)
    utilizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'rh_tokenaccesoevaluacion'

    def evaluacion(self):
        """Evaluación abierta de la empresa del empleado (la de fecha final más reciente)."""
        from django.db.models import Q
        return (Evaluacion.objects.filter(cerrada=False)
                .filter(Q(empresa_id=self.empleado.empresa_id) | Q(empresa__isnull=True))
                .order_by('-fecha_final').first())

    def vigente_hasta(self):
        """Último día en que sirve el enlace: la fecha final de la evaluación abierta (None si no hay)."""
        evaluacion = self.evaluacion()
        return evaluacion.fecha_final if evaluacion else None

    def es_valido(self):
        # Sirve mientras la evaluación esté abierta, hasta el final del día de su fecha final
        # (antes eran 5 días desde que se envió el correo)
        hasta = self.vigente_hasta()
        return not self.utilizado and hasta is not None and timezone.localdate() <= hasta

def competencias_requeridas(evaluado, tipo):
    """IDs de las competencias que lleva la evaluación de un empleado: todas las generales más sus específicas
    asignadas (igual que el panel). En la autoevaluación de quien no se evalúa no hay ninguna."""
    if tipo == 'E' and not evaluado.se_evalua:
        return set()
    generales = Competencia.objects.filter(id_clasificacion__tipo='G').values_list('id_competencia', flat=True)
    especificas = EmpleadoCompetenciaAsignada.objects.filter(id_empleado=evaluado).values_list('id_competencia_id', flat=True)
    return set(generales) | set(especificas)


class EvaluacionEntrega(models.Model):
    """Avance de cada evaluación (autoevaluación 'E' o del jefe 'J') de un empleado en un periodo.
    Queda como completa la primera vez que se contestan todas sus competencias y así se queda, aunque después
    se le asignen más: el consolidado muestra la calificación solo de las completas."""
    TIPOS = [('E', 'Autoevaluación'), ('J', 'Evaluación del jefe')]

    id_evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, db_column='id_evaluacion', verbose_name="Evaluación")
    id_empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, db_column='id_empleado', verbose_name="Evaluado")
    tipo = models.CharField(max_length=1, choices=TIPOS)
    contestadas = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0, help_text="Competencias que llevaba la evaluación en el último guardado")
    completa = models.BooleanField(default=False)
    fecha_completa = models.DateTimeField(null=True, blank=True, verbose_name="Completada el")
    actualizado = models.DateTimeField(auto_now=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, db_column='empresa')

    class Meta:
        db_table = 'rh_evaluacion_entrega'
        unique_together = ('id_evaluacion', 'id_empleado', 'tipo')
        verbose_name = "Entrega de evaluación"
        verbose_name_plural = "Entregas de evaluación"

    @classmethod
    def actualizar(cls, evaluacion, evaluado, tipo):
        """Recalcula el avance después de guardar; devuelve la entrega."""
        requeridas = competencias_requeridas(evaluado, tipo)
        contestadas = set(EvaluacionDet.objects.filter(
            id_evaluacion=evaluacion, id_empleado=evaluado, tipo=tipo, calificacion__isnull=False   # 0 = NA (no aplica): sí cuenta como contestada
        ).values_list('id_competencia_id', flat=True))
        entrega, _ = cls.objects.get_or_create(
            id_evaluacion=evaluacion, id_empleado=evaluado, tipo=tipo, defaults={'empresa_id': evaluado.empresa_id})
        entrega.contestadas = len(requeridas & contestadas)
        entrega.total = len(requeridas)
        if not entrega.completa and requeridas and requeridas <= contestadas:
            entrega.completa = True
            entrega.fecha_completa = timezone.now()
        entrega.save()
        return entrega
