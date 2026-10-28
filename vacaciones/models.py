from django.contrib.auth.models import User
from django.db import models

from rh.models import Empleado, Empresa


class PoliticaVacaciones(models.Model):
    """Reglas de vacaciones por empresa (antes `policy` del sistema en Next.js)."""
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, primary_key=True, db_column='empresa')
    sabado_habil = models.BooleanField(default=True, verbose_name="¿El sábado es día hábil?")
    dias_aviso_minimo = models.PositiveSmallIntegerField(
        default=7,
        verbose_name="Días de aviso mínimo",
        help_text="Si se solicita con menos anticipación, la solicitud se marca como caso extraordinario.",
    )
    serie_folio = models.CharField(max_length=5, default='A', verbose_name="Serie del folio")
    responsable_rh = models.CharField(
        max_length=150, blank=True, default='',
        verbose_name="Responsable de RH",
        help_text="Nombre que aparece en la firma de Recursos Humanos del formato.",
    )

    class Meta:
        db_table = 'vac_politica'
        verbose_name = "Política de vacaciones"
        verbose_name_plural = "Políticas de vacaciones"
        permissions = [
            ('autorizar_rh', 'Puede dar la autorización de RH y ver las vacaciones del personal'),
        ]

    def __str__(self):
        return f"Política de vacaciones {self.empresa_id}"


class DiaInhabil(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, db_column='empresa')
    fecha = models.DateField()
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'vac_dia_inhabil'
        verbose_name = "Día inhábil"
        verbose_name_plural = "Días inhábiles"
        unique_together = ('empresa', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y} {self.nombre}"


class SaldoVacaciones(models.Model):
    """
    Saldo reconocido a la fecha de corte. En cada aniversario posterior a
    `anios_acumulados` se suman los días de la tabla de la empresa.
    """
    empleado = models.OneToOneField(Empleado, on_delete=models.CASCADE, related_name='saldo_vacaciones')
    dias_arrastrados = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        verbose_name="Días disponibles al corte",
    )
    anios_acumulados = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Años de servicio incluidos",
        help_text="Aniversarios ya sumados en los días disponibles al corte.",
    )
    fecha_corte = models.DateField(auto_now_add=True, verbose_name="Fecha de corte")

    class Meta:
        db_table = 'vac_saldo_empleado'
        verbose_name = "Saldo de vacaciones"
        verbose_name_plural = "Saldos de vacaciones"

    def __str__(self):
        return f"{self.empleado} — {self.dias_arrastrados} días"


class SolicitudVacaciones(models.Model):
    PENDIENTE_JEFE = 'pendiente_jefe'
    PENDIENTE_RH = 'pendiente_rh'
    APROBADA = 'aprobada'
    RECHAZADA = 'rechazada'
    CANCELADA = 'cancelada'
    ESTATUS = [
        (PENDIENTE_JEFE, 'Pendiente jefe'),
        (PENDIENTE_RH, 'Pendiente RH'),
        (APROBADA, 'Aprobada'),
        (RECHAZADA, 'Rechazada'),
        (CANCELADA, 'Cancelada'),
    ]
    # Estatus que apartan días del saldo
    ESTATUS_CONSUMEN = (PENDIENTE_JEFE, PENDIENTE_RH, APROBADA)

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, db_column='empresa')
    serie = models.CharField(max_length=5, default='A')
    folio = models.PositiveIntegerField()
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name='solicitudes_vacaciones')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    dias_habiles = models.DecimalField(max_digits=5, decimal_places=1)
    motivo = models.TextField(blank=True, default='')
    estatus = models.CharField(max_length=20, choices=ESTATUS)
    extraordinaria = models.BooleanField(default=False)

    jefe = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    nota_jefe = models.TextField(blank=True, default='')
    fecha_visto_jefe = models.DateTimeField(null=True, blank=True)

    decidido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    nota_decision = models.TextField(blank=True, default='')
    fecha_decision = models.DateTimeField(null=True, blank=True)

    # Ya descontada en el saldo al corte (histórico importado): no vuelve a restarse
    liquidada = models.BooleanField(default=False)
    capturada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    fecha_creacion = models.DateTimeField()

    class Meta:
        db_table = 'vac_solicitud'
        verbose_name = "Solicitud de vacaciones"
        verbose_name_plural = "Solicitudes de vacaciones"
        unique_together = ('empresa', 'folio')
        ordering = ['-fecha_creacion', '-folio']

    def __str__(self):
        return f"{self.folio_texto} {self.empleado}"

    @property
    def folio_texto(self):
        return f"{self.serie}-{self.folio}"

    @property
    def esta_pendiente(self):
        return self.estatus in (self.PENDIENTE_JEFE, self.PENDIENTE_RH)
