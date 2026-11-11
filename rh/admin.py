from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.core.mail import send_mail
from django.db import models  
from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
import openpyxl
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.sites import UnfoldAdminSite  # ⬅️ ¡ESTA ES LA LÍNEA MÁGICA QUE FALTA!
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db import connection
from .models import TokenAccesoEvaluacion, Empleado, Empresa
from core_app.models import AccesoEmpresa
import uuid
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from unfold.admin import ModelAdmin
from unfold.forms import ActionForm

class CustomActionForm(ActionForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'action' in self.fields:
            self.fields['action'].empty_label = "Seleccionar acción..."
            # Forzamos las opciones para borrar el "Select action" en inglés de la lista
            choices = [('', 'Seleccionar acción...')]
            for option_key, option_label in self.fields['action'].choices:
                if option_key != '':
                    choices.append((option_key, option_label))
            self.fields['action'].choices = choices


class CustomAdminSite(UnfoldAdminSite):
    index_template = "admin/index_dashboard.html"

    def each_context(self, request):
        context = super().each_context(request)
        path = request.path.lower()

        # 1. Módulo Seguridad del Sitio (Usuarios y Grupos de Auth)
        if any(k in path for k in ['/admin/auth/', '/auth/', '/user/', '/group/']):
            header_text = "Seguridad del Sitio"

        # 2. Módulo Tablas Dinámicas / Reportes
        elif any(k in path for k in ['/inventario/', '/reportes/', 'pivot']):
            header_text = "Tablas Dinámicas"

        # 3. Módulo Recursos Humanos (Evaluaciones, Empleados, Puestos, etc.)
        elif any(k in path for k in ['/admin/rh/', '/admin/vacaciones/', 'evaluacion', 'empleado', 'puesto', 'departamento', 'competencia', 'resumen', 'panel']):
            header_text = "Recursos Humanos"

        # 4. Dashboard / Inicio
        else:
            header_text = "Portal Empresarial"

        # Sobrescribir en el contexto de Unfold para la plantilla
        context['site_header'] = header_text
        context['site_title'] = header_text
        return context

    def index(self, request, extra_context=None):

        # 1. Obtener la empresa activa de la sesión
        empresa_activa = request.session.get('empresa_activa') or request.session.get('empresa_id')
        
        extra_context = extra_context or {}

        # El tablero de avance de evaluaciones solo lo ve quien tiene acceso a "Consolidado Resultados"
        puede_ver_tablero = request.user.is_superuser or request.user.has_perm('rh.ver_consolidado_resultados')
        extra_context["mostrar_tablero"] = puede_ver_tablero
        if not puede_ver_tablero:
            return super().index(request, extra_context=extra_context)

        departamentos_dict = {}
        jefes_dict = {} 
        
        total_global_empleados = 0
        total_ambas_completadas_global = 0
        total_auto_global = 0
        total_jefe_global = 0


        with connection.cursor() as cursor:
            cursor.execute("""
                    SELECT 
                        departamento, 
                        jefe, 
                        numempleados, 
                        autoevaluados, 
                        evaluados,
                        ambas  
                    FROM rh_vista_dashboard_departamentos
                    WHERE empresa = %s
                """, [empresa_activa])

            rows = cursor.fetchall()
            
            for row in rows:
                dep_nombre = row[0] or "Sin Departamento"
                jefe_nombre = row[1] or "Sin Jefe Asignado"
                
                num_emp = int(row[2] or 0)
                auto_ev = int(row[3] or 0)
                jefe_ev = int(row[4] or 0)
                ambas_ev = int(row[5] or 0)  

                # 1. MANTENER DEPARTAMENTOS INTACTOS
                if dep_nombre not in departamentos_dict:
                    departamentos_dict[dep_nombre] = {
                        'num_empleados': 0,
                        'auto_evaluados': 0,
                        'evaluados': 0,
                        'porcentaje': 0
                    }
                
                departamentos_dict[dep_nombre]['num_empleados'] += num_emp
                departamentos_dict[dep_nombre]['auto_evaluados'] += auto_ev
                departamentos_dict[dep_nombre]['evaluados'] += jefe_ev
                
                total_dep = departamentos_dict[dep_nombre]['num_empleados']
                autos_dep = departamentos_dict[dep_nombre]['auto_evaluados']
                jefes_dep = departamentos_dict[dep_nombre]['evaluados']
                
                # ➡️ CORRECCIÓN AQUÍ: El total de evaluaciones esperadas es el doble del número de empleados (Auto + Jefe)
                evaluaciones_totales_esperadas = total_dep * 2
                evaluaciones_realizadas = autos_dep + jefes_dep
                
                if evaluaciones_totales_esperadas > 0:
                    departamentos_dict[dep_nombre]['porcentaje'] = round((evaluaciones_realizadas / evaluaciones_totales_esperadas) * 100)
                else:
                    departamentos_dict[dep_nombre]['porcentaje'] = 0

                # 2. ACTUALIZACIÓN DE KPIS GLOBALES
                total_global_empleados += num_emp
                total_auto_global += auto_ev
                total_jefe_global += jefe_ev
                total_ambas_completadas_global += ambas_ev  
                
                # 3. AGRUPACIÓN Y SUMARIZACIÓN POR JEFE
                if jefe_nombre not in jefes_dict:
                    jefes_dict[jefe_nombre] = {
                        'nombre': jefe_nombre,
                        'total_empleados': 0,
                        'auto_contestadas': 0,
                        'jefe_contestadas': 0,
                    }
                
                jefes_dict[jefe_nombre]['total_empleados'] += num_emp
                jefes_dict[jefe_nombre]['auto_contestadas'] += auto_ev
                jefes_dict[jefe_nombre]['jefe_contestadas'] += jefe_ev

        # --- POST-PROCESAMIENTO DE JAFES ---
        jefes_data = []
        for jefe_nombre, data in jefes_dict.items():
            tot_emp = data['total_empleados']
            auto_cont = data['auto_contestadas']
            jefe_cont = data['jefe_contestadas']

            auto_pct = round((auto_cont / tot_emp * 100), 1) if tot_emp > 0 else 0.0
            jefe_pct = round((jefe_cont / tot_emp * 100), 1) if tot_emp > 0 else 0.0

            color_auto = "#ef4444" if auto_pct < 40 else ("#f59e0b" if auto_pct < 85 else "#72a651")
            color_jefe = "#ef4444" if jefe_pct < 40 else ("#f59e0b" if jefe_pct < 85 else "#72a651")

            jefes_data.append({
                'nombre': jefe_nombre,
                'total_empleados': tot_emp,
                'auto_contestadas': auto_cont,
                'auto_pct': auto_pct,
                'color_auto': color_auto,
                'jefe_contestadas': jefe_cont,
                'jefe_pct': jefe_pct,
                'color_jefe': color_jefe,
            })

        jefes_data = sorted(jefes_data, key=lambda x: x['nombre'])

        # --- CÁLCULO DE KPIS GLOBAL ---
        pct_general = round((total_ambas_completadas_global / total_global_empleados * 100), 1) if total_global_empleados > 0 else 0
        pct_auto = round((total_auto_global / total_global_empleados * 100), 1) if total_global_empleados > 0 else 0
        pct_jefe = round((total_jefe_global / total_global_empleados * 100), 1) if total_global_empleados > 0 else 0

        offset_general = round(251.2 * (1 - (pct_general / 100)), 1)
        offset_auto = round(251.2 * (1 - (pct_auto / 100)), 1)
        offset_jefe = round(251.2 * (1 - (pct_jefe / 100)), 1)

        extra_context["global_kpis"] = {
            "general_completadas": total_ambas_completadas_global,
            "general_porcentaje": pct_general,
            "general_offset": offset_general,
            "auto_contestadas": total_auto_global,
            "auto_porcentaje": pct_auto,
            "auto_offset": offset_auto,
            "jefe_contestadas": total_jefe_global,
            "jefe_porcentaje": pct_jefe,
            "jefe_offset": offset_jefe,
        }

        extra_context["departamentos"] = departamentos_dict
        extra_context["jefes_data"] = jefes_data

        return super().index(request, extra_context=extra_context)

# Instanciación del sitio personalizado
admin_site = CustomAdminSite(name='custom_admin')

# Desasociamos los registros por defecto (en caso de ser necesario)
# e incorporamos el soporte de visualización para tu panel personalizado de Unfold
try:
    admin.site.unregister(User)
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

# Registramos Usuarios y Grupos para que tu URLconf sepa que existen en /admin/
# Registramos Usuarios y Grupos para que tu URLconf sepa que existen en tu 'admin_site' personalizado de Unfold
class AccesoEmpresaInline(StackedInline):
    """Empresas a las que entra el usuario y sus grupos/permisos en cada una (se suman a los globales)."""
    model = AccesoEmpresa
    extra = 0
    filter_horizontal = ('grupos', 'permisos')
    fields = ('empresa', 'activo', 'grupos', 'permisos')


class CopiarAccesosForm(forms.Form):
    origen = forms.ModelChoiceField(queryset=Empresa.objects.filter(activa=True), label="Copiar de la empresa")
    destino = forms.ModelChoiceField(queryset=Empresa.objects.filter(activa=True), label="A la empresa")
    reemplazar = forms.BooleanField(
        required=False, label="Reemplazar",
        help_text="Si se marca, en la empresa destino quedan exactamente los grupos y permisos de la de origen. "
                  "Si no, se agregan a los que ya tenga.")

    def clean(self):
        datos = super().clean()
        if datos.get('origen') and datos.get('origen') == datos.get('destino'):
            raise forms.ValidationError("La empresa de origen y la de destino deben ser distintas.")
        return datos


@admin.register(User, site=admin_site)  # 🌟 Agregamos 'site=admin_site' para que se vinculen a tu dashboard
class UserAdmin(BaseUserAdmin, ModelAdmin):
    inlines = [AccesoEmpresaInline]
    actions = ['copiar_accesos_entre_empresas']

    @admin.action(description="Copiar accesos de una empresa a otra")
    def copiar_accesos_entre_empresas(self, request, queryset):
        form = CopiarAccesosForm(request.POST if 'aplicar' in request.POST else None)
        if 'aplicar' in request.POST and form.is_valid():
            origen, destino = form.cleaned_data['origen'], form.cleaned_data['destino']
            copiados, sin_origen = 0, []
            for usuario in queryset:
                acceso_origen = AccesoEmpresa.objects.filter(usuario=usuario, empresa=origen).first()
                if not acceso_origen:
                    sin_origen.append(usuario.username)
                    continue
                acceso_destino, _ = AccesoEmpresa.objects.get_or_create(usuario=usuario, empresa=destino)
                acceso_destino.activo = acceso_origen.activo
                acceso_destino.save(update_fields=['activo'])
                if form.cleaned_data['reemplazar']:
                    acceso_destino.grupos.set(acceso_origen.grupos.all())
                    acceso_destino.permisos.set(acceso_origen.permisos.all())
                else:
                    acceso_destino.grupos.add(*acceso_origen.grupos.all())
                    acceso_destino.permisos.add(*acceso_origen.permisos.all())
                copiados += 1
            self.message_user(request, f"Accesos copiados de {origen.pk} a {destino.pk} para {copiados} usuario(s).", messages.SUCCESS)
            if sin_origen:
                self.message_user(request, f"Sin acceso en {origen.pk} (no se copió nada): {', '.join(sin_origen)}", messages.WARNING)
            return None

        return render(request, 'admin/copiar_accesos_empresa.html', {
            **self.admin_site.each_context(request),
            'title': "Copiar accesos de una empresa a otra",
            'form': form,
            'usuarios': queryset,
            'accion': 'copiar_accesos_entre_empresas',
            'opts': self.model._meta,
        })

@admin.register(Group, site=admin_site) # 🌟 Agregamos 'site=admin_site' para que se vinculen a tu dashboard
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


# Importación explícita de todos los modelos requeridos
from .models import (
    Puesto, Departamento, Empleado, CompetenciaClasificacion, 
    Competencia, Evaluacion, EvaluacionDet, ClasificacionPorPuesto, 
    ClasificacionPorEmpleado, EmpleadoCompetenciaAsignada
)



class CatalogosOrdenadosAdmin(admin.ModelAdmin):
    """
    Clase base para que todos los combos (ForeignKeys) del sistema
    se ordenen alfabéticamente de forma automática, sin alterar el listado principal.
    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # 1. Obtenemos el modelo al que apunta esta clave heredada
        target_model = db_field.remote_field.model
        campos = [f.name for f in target_model._meta.fields]

        # 2. Si el modelo tiene un campo 'nombre_largo' o 'descripcion', ordenamos por él
        if 'nombre_largo' in campos:
            kwargs["queryset"] = target_model.objects.order_by('nombre_largo')
        elif 'descripcion' in campos:
            kwargs["queryset"] = target_model.objects.order_by('descripcion')
        elif 'nombre' in campos:
            kwargs["queryset"] = target_model.objects.order_by('nombre')

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
class ExcelUploadForm(forms.Form):
    archivo_excel = forms.FileField(label="Selecciona el archivo de Excel (.xlsx)")


# =========================================================================
#  CLASE BASE PARA IMPORTACIÓN EXCEL
# =========================================================================
# =========================================================================
#  CLASE BASE PARA IMPORTACIÓN EXCEL (CORREGIDA)
# =========================================================================
# =========================================================================
#  CLASE BASE PARA IMPORTACIÓN EXCEL (MÉTODO EXPORTAR INTEGRADO)
# =========================================================================
class ExcelImportAdmin(ModelAdmin):
    import_template = "admin/importar_excel.html"
    change_list_template = "admin/carga_masiva_change_list.html"
    # 🌟 APLICADO GLOBALMENTE: Todos los catálogos heredarán esto automáticamente
    action_form = CustomActionForm
    action_submit_label = "Ejecutar"
    
    model_class = None       
    pk_field_name = None     
    excel_columns = []       

    list_per_page = 25
    list_select_related = True

    # 1. Generador de URLs para los botones del template personalizado
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        if self.model:
            app_label = self.model._meta.app_label
            model_name = self.model._meta.model_name
            query_string = request.GET.urlencode()
            
            url_exportar = f"/admin/{app_label}/{model_name}/exportar-excel/"
            if query_string:
                url_exportar += f"?{query_string}"
                
            extra_context['url_exportar_excel'] = url_exportar
            
        return super().changelist_view(request, extra_context=extra_context)

    # 2. Botones de acción rápidos (Editar/Eliminar)
    def acciones_rh(self, obj):
        app_label = obj._meta.app_label
        model_name = obj._meta.model_name
        editar_url = f"/admin/{app_label}/{model_name}/{obj.pk}/change/"
        eliminar_url = f"/admin/{app_label}/{model_name}/{obj.pk}/delete/"
        
        return format_html(
            '<a href="{}" title="Editar" style="'
            'display: inline-flex !important; align-items: center !important; justify-content: center !important; '
            'width: 26px !important; height: 26px !important; border-radius: 4px !important; margin-right: 6px !important; '
            'background-color: #72a651 !important; color: #ffffff !important; font-weight: bold !important; '
            'text-decoration: none !important; font-size: 14px !important; opacity: 1 !important; line-height: 1 !important;">'
            '&#9998;'
            '</a>'
            '<a href="{}" title="Eliminar" style="'
            'display: inline-flex !important; align-items: center !important; justify-content: center !important; '
            'width: 26px !important; height: 26px !important; border-radius: 4px !important; '
            'background-color: #de3a3a !important; color: #ffffff !important; font-weight: bold !important; '
            'text-decoration: none !important; font-size: 13px !important; opacity: 1 !important; line-height: 1 !important;">'
            '&#10006;'
            '</a>',
            editar_url, eliminar_url
        )
    acciones_rh.short_description = "Acciones"

    # 3. Registra rutas de importación y exportación
    def get_urls(self):
        urls = super().get_urls()
        if not self.model:
            return urls

        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name

        custom_urls = [
            path(
                'importar-excel/', 
                self.admin_site.admin_view(self.import_excel_view), 
                name=f'{app_label}_{model_name}_import_excel'
            ),
            path(
                'exportar-excel/', 
                self.admin_site.admin_view(self.exportar_catalogo_view), 
                name=f'{app_label}_{model_name}_exportar_excel'
            ),
        ]
        return custom_urls + urls

    # 4. Motor de procesamiento de carga masiva multitenant
    # 4. Motor de procesamiento de carga masiva multitenant con mapeo de catálogos
    def import_excel_view(self, request):
        if request.method == "POST":
            excel_file = request.FILES.get("excel_file")
            empresa_activa_id = request.session.get('empresa_id')
            
            if not excel_file:
                messages.error(request, "Por favor, selecciona un archivo válido.")
                return redirect(f"/admin/{self.model_class._meta.app_label}/{self.model_class._meta.model_name}/")

            if not excel_file.name.endswith(('.xlsx', '.xls')):
                messages.error(request, "El archivo debe ser un Excel (.xlsx o .xls).")
                return redirect(f"/admin/{self.model_class._meta.app_label}/{self.model_class._meta.model_name}/")

            try:
                wb = openpyxl.load_workbook(excel_file, data_only=True)
                sheet = wb.active

                header_row = [str(cell.value).strip().lower() if cell.value is not None else "" for cell in sheet[1]]
                col_map = {name: idx for idx, name in enumerate(header_row) if name}

                success_count = 0
                error_count = 0

                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    if not any(row):  
                        continue

                    data = {}
                    for col_name in self.excel_columns:
                        posibles_nombres = [
                            col_name.lower(),
                            col_name.lower().removesuffix('_id'),
                            col_name.lower() + '_id'
                        ]
                        
                        idx = None
                        for nombre in posibles_nombres:
                            if nombre in col_map:
                                idx = col_map[nombre]
                                break

                        if idx is not None and idx < len(row):
                            val = row[idx]
                            if isinstance(val, str):
                                val = val.strip()
                            data[col_name] = val

                    # 🌟 ASIGNACIÓN AUTOMÁTICA DE LA EMPRESA ACTIVA
                    if hasattr(self.model_class, 'empresa') and empresa_activa_id:
                        data['empresa_id'] = empresa_activa_id
                        data.pop('empresa', None)  # Previene conflicto con ForeignKeys de texto

                    # 🌟 TRADUCCIÓN DE IDs EXTERNOS PARA PUESTO Y DEPARTAMENTO (EN EMPLEADO)
                    if self.model_class == Empleado and empresa_activa_id:
                        # 1. Resolver Puesto
                        puesto_ext = data.pop('id_puesto', None) or data.pop('id_puesto_id', None)
                        if puesto_ext:
                            puesto_obj = Puesto.objects.filter(
                                id_puesto=puesto_ext, 
                                empresa_id=empresa_activa_id
                            ).first()
                            if puesto_obj:
                                data['id_puesto_id'] = puesto_obj.id
                            else:
                                messages.warning(request, f"Fila {row_idx}: No se encontró el Puesto ID '{puesto_ext}' para esta empresa.")
                                continue

                        # 2. Resolver Departamento
                        depto_ext = data.pop('id_departamento', None) or data.pop('id_departamento_id', None)
                        if depto_ext:
                            depto_obj = Departamento.objects.filter(
                                id_departamento=depto_ext, 
                                empresa_id=empresa_activa_id
                            ).first()
                            if depto_obj:
                                data['id_departamento_id'] = depto_obj.id 
                            else:
                                messages.warning(request, f"Fila {row_idx}: No se encontró el Departamento ID '{depto_ext}' para esta empresa.")
                                continue

                    pk_lower = self.pk_field_name.lower()
                    pk_idx = col_map.get(pk_lower) or col_map.get(pk_lower.removesuffix('_id')) or col_map.get(pk_lower + '_id')
                    pk_value = row[pk_idx] if pk_idx is not None and pk_idx < len(row) else None

                    if pk_value is not None and str(pk_value).strip() != "":
                        try:
                            pk_value = int(float(str(pk_value).strip()))
                        except (ValueError, TypeError):
                            error_count += 1
                            messages.warning(request, f"Error en fila {row_idx}: El ID debe ser un número entero. Se obtuvo: {pk_value}")
                            continue
                    else:
                        pk_value = None

                    if pk_value:
                        try:
                            # 🌟 BÚSQUEDA Y ACTUALIZACIÓN CONSIDERANDO LA COMBINACIÓN EMPRESA + ID_LOCAL
                            filter_kwargs = {self.pk_field_name: pk_value}
                            if hasattr(self.model_class, 'empresa') and empresa_activa_id:
                                filter_kwargs['empresa_id'] = empresa_activa_id

                            defaults_data = {k: v for k, v in data.items() if k != self.pk_field_name}
                            
                            instance, created = self.model_class.objects.update_or_create(
                                **filter_kwargs,
                                defaults=defaults_data
                            )
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            messages.warning(request, f"Error en fila {row_idx} al procesar ID {pk_value}: {e}")
                    else:
                        try:
                            self.model_class.objects.create(**data)
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            messages.warning(request, f"Error en fila {row_idx} (Sin ID): {e}")

                messages.success(request, f"Importación completada. Registros procesados: {success_count}. Errores: {error_count}")
                
            except Exception as e:
                messages.error(request, f"Error crítico al procesar el archivo: {e}")
                
        return redirect(f"/admin/{self.model_class._meta.app_label}/{self.model_class._meta.model_name}/")

    # 5. Exportación del catálogo filtrado por la empresa seleccionada
    def exportar_catalogo_view(self, request):
        if not self.model:
            raise Http404("Modelo no configurado.")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Catálogo {self.model._meta.model_name.capitalize()}"

        columnas = self.excel_columns if self.excel_columns else [field.name for field in self.model._meta.fields]
        ws.append(columnas)

        # 🌟 UTILIZA get_queryset PARA DEDUCR SOLO LA DATA PERTINENTE A LA EMPRESA ACTIVA
        queryset = self.get_queryset(request)
        
        for objeto in queryset:
            fila = [getattr(objeto, col, "") for col in columnas]
            fila_limpia = [str(val) if val is not None else "" for val in fila]
            ws.append(fila_limpia)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="catalogo_{self.model._meta.model_name}.xlsx"'
        wb.save(response)
        return response


class EmpresaFilterAdmin(ExcelImportAdmin):
    """
    Clase base que filtra la información según la empresa en sesión.
    Si el registro tiene empresa=NULL se considera GENERAL y se muestra a todos.
    """
    exclude = ('empresa',)  # 👈 Oculta el campo Empresa en todos los catálogos heredados
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        empresa_activa = request.session.get('empresa_activa') or request.session.get('empresa_id')
        
        # Verifica si el modelo actual tiene la columna 'empresa' o 'empresa_id'
        field_names = [f.name for f in self.model._meta.get_fields()]
        
        if empresa_activa:
            if 'empresa' in field_names:
                return qs.filter(empresa=empresa_activa)
            elif 'empresa_id' in field_names:
                return qs.filter(empresa_id=empresa_activa)
                
        return qs

    def save_model(self, request, obj, form, change):
        # Asigna automáticamente la empresa activa de la sesión si no tiene una asignada
        if hasattr(obj, 'empresa') and not obj.empresa_id:
            obj.empresa_id = request.session.get('empresa_activa') or request.session.get('empresa_id')
        super().save_model(request, obj, form, change)

# ==========================================
#   INLINE: CLASIFICACIÓN POR PUESTO
# ==========================================
class ClasificacionPorPuestoInlineForm(forms.ModelForm):
    class Meta:
        model = ClasificacionPorPuesto
        fields = ('id_clasificacion',)
        widgets = {
            'id_clasificacion': forms.Select(attrs={
                'style': 'width: 100% !important; min-width: 100% !important; height: 38px !important; display: block !important;'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🌟 FILTRO MÁGICO: Limitamos las opciones del combo a solo las específicas ('E') ordenadas alfabéticamente
        self.fields['id_clasificacion'].queryset = CompetenciaClasificacion.objects.filter(tipo='E').order_by('descripcion')

        if self.instance and self.instance.pk:
            valor_actual = self.instance.id_clasificacion_id
            self.fields['id_clasificacion'].widget.value = valor_actual
            self.initial['id_clasificacion'] = valor_actual
            self.instance.__class__.__str__ = lambda self: ""
            self.instance.id_clasificacion = None
        else:
            self.initial['id_clasificacion'] = ""


class ClasificacionPorPuestoInline(TabularInline):
    model = ClasificacionPorPuesto
    form = ClasificacionPorPuestoInlineForm
    extra = 1  # 💡 Cambiado a 1 para que se vea más limpio en el panel de Unfold
    fields = ('id_clasificacion',)


# ==========================================
#   INLINE: CLASIFICACIÓN POR EMPLEADO
# ==========================================
class ClasificacionPorEmpleadoInlineForm(forms.ModelForm):
    nueva_competencia_texto = forms.CharField(
        required=False,
        label="Competencia Exclusiva (Captura libre)",
        widget=forms.TextInput(attrs={
            'style': 'width: 100% !important; min-width: 250px !important; height: 38px !important; padding: 0 10px !important;',
            'placeholder': 'Escribe aquí la competencia solo para este empleado...'
        })
    )

    class Meta:
        model = ClasificacionPorEmpleado
        fields = ('id_clasificacion', 'nueva_competencia_texto', 'motivo')
        widgets = {
            'id_clasificacion': forms.Select(attrs={
                'style': 'width: 100% !important; min-width: 200px !important; height: 38px !important;'
            }),
            'motivo': forms.TextInput(attrs={
                'style': 'width: 100% !important; min-width: 150px !important; height: 38px !important;'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.competencia_exclusiva_id:
            self.initial['nueva_competencia_texto'] = self.instance.competencia_exclusiva.descripcion
        
        if self.instance and self.instance.pk:
            valor_actual = self.instance.id_clasificacion_id
            self.fields['id_clasificacion'].widget.value = valor_actual
            self.initial['id_clasificacion'] = valor_actual
            self.instance.__class__.__str__ = lambda self: ""
            self.instance.id_clasificacion = None
        else:
            self.initial['id_clasificacion'] = ""

    def save(self, commit=True):
        instance = super().save(commit=False)
        texto_competencia = self.cleaned_data.get('nueva_competencia_texto')
        id_clasif = self.cleaned_data.get('id_clasificacion') or instance.id_clasificacion

        if texto_competencia and id_clasif:
            from .models import Competencia
            if instance.competencia_exclusiva:
                comp = instance.competencia_exclusiva
                comp.descripcion = texto_competencia
                comp.id_clasificacion = id_clasif
                comp.save()
            else:
                comp = Competencia.objects.create(
                    id_clasificacion=id_clasif,
                    descripcion=texto_competencia
                )
                instance.competencia_exclusiva = comp
        elif not texto_competencia:
            instance.competencia_exclusiva = None

        if commit:
            instance.save()
        return instance


class ClasificacionPorEmpleadoInline(TabularInline):
    model = ClasificacionPorEmpleado
    form = ClasificacionPorEmpleadoInlineForm
    extra = 1
    fields = ('id_clasificacion', 'nueva_competencia_texto', 'motivo')


# ==========================================
#   INLINE: COMPETENCIAS
# ==========================================
class CompetenciaInlineForm(forms.ModelForm):
    descripcion = forms.CharField(
        widget=forms.TextInput(attrs={
            'style': 'width: 100% !important; min-width: 100% !important; height: 38px !important; display: block !important; padding: 0 10px !important;'
        }),
        required=False,
    )

    class Meta:
        model = Competencia
        fields = ('descripcion',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            valor_actual = self.instance.descripcion
            self.fields['descripcion'].widget.value = valor_actual
            self.initial['descripcion'] = valor_actual
            self.instance.descripcion = ""  
        else:
            self.initial['descripcion'] = ""


class CompetenciaInline(TabularInline):
    model = Competencia
    form = CompetenciaInlineForm
    extra = 3  
    fields = ('descripcion',)


# =========================================================================
#   FORMULARIO PRINCIPAL: MATRIZ CHECKLIST DE SELECCIÓN INTELIGENTE
# =========================================================================
class EmpleadoAdminForm(forms.ModelForm):
    competencias_seleccionadas = forms.ModelMultipleChoiceField(
        queryset=Competencia.objects.none(),
        widget=forms.MultipleHiddenInput(),
        required=False,
        label=""
    )

    class Meta:
        model = Empleado
        fields = '__all__'
        exclude = ('empresa',)  # 👈 Oculta el selector de Empresa en el formulario de Empleado

        # 🌟 AGREGA ESTA PROPIEDAD AQUÍ ABAJO:
        # 🌟 AQUÍ ESPECIFICAS EL ANCHO IDÉNTICO PARA TODOS LOS CAMPOS
        widgets = {
            # 🟢 CAMPOS AL 75% DE SU CONTENEDOR (o w-3/4 con Tailwind)
            'nombre_largo': forms.TextInput(attrs={
                'style': 'width: 50% !important;',
                # O si prefieres Tailwind: 'class': 'w-3/4'
            }),
            'CorreoElectronico': forms.EmailInput(attrs={
                'style': 'width: 50% !important;',
            }),
            'id_jefe': forms.Select(attrs={
                'style': 'width: 50% !important;',
            }),

            # 🔵 CAMPOS AL 30% DE SU CONTENEDOR (o w-1/3 con Tailwind)
            'id_departamento': forms.Select(attrs={
                'style': 'width: 20% !important;',
                # O si prefieres Tailwind: 'class': 'w-1/3'
            }),
            'id_puesto': forms.Select(attrs={
                'style': 'width: 20% !important;',
            }),
            'user': forms.Select(attrs={
                'style': 'width: 10% !important;',
            }),
            'estado_empleado': forms.Select(attrs={
                'style': 'width: 10% !important;',
            }),
            'fechaalta': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'style': 'width: 10% !important;'}
            ),
        }

    def __init__(self, *args, **kwargs):
        # 1. Extraemos el objeto 'request' si fue proporcionado desde el Admin
        self.request = kwargs.pop('request', None)        
        super().__init__(*args, **kwargs)

        # 2. Obtenemos la empresa activa seleccionada en la sesión
        empresa_activa = None
        if self.request:
            empresa_activa = self.request.session.get('empresa_activa') or self.request.session.get('empresa_id')

        # 3. Filtrar Departamentos por Empresa Activa
        if 'id_departamento' in self.fields:
            qs_dep = Departamento.objects.all()
            if empresa_activa:
                qs_dep = qs_dep.filter(empresa_id=empresa_activa)
            self.fields['id_departamento'].queryset = qs_dep.order_by('descripcion')

        # 4. Filtrar Puestos por Empresa Activa
        if 'id_puesto' in self.fields:
            qs_puesto = Puesto.objects.all()
            if empresa_activa:
                qs_puesto = qs_puesto.filter(empresa_id=empresa_activa)
            self.fields['id_puesto'].queryset = qs_puesto.order_by('descripcion')

        # 5. Filtrar Jefes por Empresa Activa
        if 'id_jefe' in self.fields:
            qs_jefe = Empleado.objects.all()
            if empresa_activa:
                qs_jefe = qs_jefe.filter(empresa_id=empresa_activa)
            self.fields['id_jefe'].queryset = qs_jefe.order_by('nombre_largo')

        # 🌟 NUEVO: FORZAR ORDENAMIENTO ALFABÉTICO EN LOS COMBOS PRINCIPALES DEL FORMULARIO
        if 'user' in self.fields:
            self.fields['user'].queryset = self.fields['user'].queryset.order_by('username')
        

        if self.instance and self.instance.pk:
            empleado_id = self.instance.pk
            # 1. Obtenemos el ID del puesto de la base de datos física de forma segura
            puesto_id = self.instance.id_puesto_id

            # --- UNIVERSO A: Competencias que le corresponden por su Puesto ---
            clasif_puesto_ids = list(ClasificacionPorPuesto.objects.filter(
                id_puesto_id=puesto_id
            ).values_list('id_clasificacion_id', flat=True))

            competencias_del_puesto_ids = list(Competencia.objects.filter(
                id_clasificacion_id__in=clasif_puesto_ids
            ).values_list('id_competencia', flat=True))

            # --- UNIVERSO B: Competencias que el empleado ya tiene guardadas ---
            competencias_guardadas_ids = list(EmpleadoCompetenciaAsignada.objects.filter(
                id_empleado_id=empleado_id
            ).values_list('id_competencia_id', flat=True))

            # --- UNIFICACIÓN DE AMBOS UNIVERSOS (Igual al UNION de tu SQL) ---
            todas_competencias_ids = list(set(competencias_del_puesto_ids + competencias_guardadas_ids))

            # 2. Reconstruimos el queryset final limpio y ordenado
            queryset_competencias = Competencia.objects.filter(
                id_competencia__in=todas_competencias_ids
            ).select_related('id_clasificacion').order_by('id_clasificacion__descripcion', 'descripcion')

            # 3. Asignamos de forma explícita al campo para desactivar el candado de Django
            self.fields['competencias_seleccionadas'].queryset = queryset_competencias
            self.fields['competencias_seleccionadas'].initial = competencias_guardadas_ids

            # Guardamos para change_view
            self.queryset_competencias_custom = queryset_competencias
            self.competencias_iniciales_custom = competencias_guardadas_ids
        else:
            self.queryset_competencias_custom = Competencia.objects.none()
            self.competencias_iniciales_custom = []


# =========================================================================
#   REGISTRO DE CATÁLOGOS EN EL ADMINISTRADOR
# =========================================================================

class PuestoAdmin(EmpresaFilterAdmin):
    model_class = Puesto
    pk_field_name = 'id_puesto'
    excel_columns = ['id_puesto', 'descripcion']
    list_display = ('id_puesto', 'descripcion', 'acciones_rh')
    search_fields = ('descripcion',)
    inlines = [ClasificacionPorPuestoInline]

#admin.site.register(Puesto, PuestoAdmin)
admin_site.register(Puesto, PuestoAdmin)

class DepartamentoAdmin(EmpresaFilterAdmin):
    model_class = Departamento
    pk_field_name = 'id_departamento'
    exclude = ('empresa',)  # 👈 Asegura que se excluya de la vista
    excel_columns = ['id_departamento', 'descripcion']
    list_display = ('id_departamento', 'descripcion', 'acciones_rh')
    search_fields = ('descripcion',)

# @admin.action(description='Enviar Enlaces de evaluación por Correo')
# def enviar_enlaces_magicos(modeladmin, request, queryset):
#     # 1. De los empleados QUE SELECCIONASTE en la lista, filtramos los que tienen correo válido
#     empleados_seleccionados = queryset.exclude(CorreoElectronico__isnull=True).exclude(CorreoElectronico='')
    
#     # 2. Obtenemos los IDs de todos los que son jefes en todo el sistema
#     jefes_ids = Empleado.objects.exclude(id_jefe__isnull=True).values_list('id_jefe', flat=True).distinct()
    
#     # 3. Aplicamos el filtro OR pero únicamente sobre los empleados SELECCIONADOS en el Admin
#     empleados_a_procesar = empleados_seleccionados.filter(
#         Q(se_evalua=True) | Q(id_empleado__in=jefes_ids)
#     )
    
#     if not empleados_a_procesar.exists():
#         modeladmin.message_user(
#             request, 
#             "Ninguno de los empleados seleccionados cumple con las condiciones (se_evalua=True o ser Jefe) o no tienen correo válido.", 
#             messages.WARNING
#         )
#         return

#     # 4. Guardamos los IDs de los seleccionados válidos en la sesión
#     empleados_ids = list(empleados_a_procesar.values_list('id_empleado', flat=True).distinct())
    
#     session_key = f"envio_correos_{uuid.uuid4().hex}"
#     request.session[session_key] = {
#         'empleados_ids': empleados_ids,
#         'procesados': 0,
#         'total': len(empleados_ids),
#         'app_label': queryset.model._meta.app_label,
#         'model_name': queryset.model._meta.model_name,
#     }

#     return redirect(f"/admin/procesar-evaluaciones-loading/{session_key}/")

@admin.action(description='Enviar Enlaces de evaluación por Correo (A todo el personal aplicable)')
def enviar_enlaces_magicos(modeladmin, request, queryset):
    # 1. Tomamos la evaluación seleccionada en la lista
    evaluacion_seleccionada = queryset.first()
    if not evaluacion_seleccionada:
        modeladmin.message_user(request, "Por favor, selecciona una evaluación.", messages.ERROR)
        return

    # 2. Obtenemos todos los empleados del sistema con correo electrónico válido
    empleados_con_correo = Empleado.objects.exclude(CorreoElectronico__isnull=True).exclude(CorreoElectronico='')

    # 3. Identificamos quiénes son jefes (los que aparecen en el campo 'id_jefe' de otros empleados)
    jefes_ids = Empleado.objects.exclude(id_jefe__isnull=True).values_list('id_jefe', flat=True).distinct()

    # 4. Filtramos: que se evalúen O que sean jefes de alguien
    empleados_a_procesar = empleados_con_correo.filter(
        Q(se_evalua=True) | Q(id__in=jefes_ids)
    )

    if not empleados_a_procesar.exists():
        modeladmin.message_user(
            request, 
            "Ningún empleado cumple con las condiciones (se_evalua=True o ser Jefe) o no tienen correo válido.", 
            messages.WARNING
        )
        return

    # 5. Guardamos la lista de IDs a procesar en la sesión para la pantalla de carga (Loading)
    empleados_ids = list(empleados_a_procesar.values_list('id', flat=True).distinct())
    
    session_key = f"envio_correos_{uuid.uuid4().hex}"
    request.session[session_key] = {
        'empleados_ids': empleados_ids,
        'evaluacion_id': evaluacion_seleccionada.id_evaluacion, # Asociamos la evaluación seleccionada
        'procesados': 0,
        'total': len(empleados_ids),
        'app_label': 'rh',
        'model_name': 'evaluacion',
    }

    return redirect(f"/admin/procesar-evaluaciones-loading/{session_key}/")


# =========================================================================
# ACCIÓN 2: Para el Modelo "Empleado" (Catálogo de Empleados)
# =========================================================================
@admin.action(description='Enviar Enlaces de evaluación a los empleados seleccionados')
def enviar_enlaces_seleccionados(modeladmin, request, queryset):
    # 1. Filtramos del queryset seleccionado los que tienen correo electrónico válido
    empleados_a_procesar = queryset.exclude(CorreoElectronico__isnull=True).exclude(CorreoElectronico='')

    if not empleados_a_procesar.exists():
        modeladmin.message_user(
            request, 
            "Ninguno de los empleados seleccionados tiene un correo electrónico válido registrado.", 
            messages.WARNING
        )
        return

    # 2. Obtenemos la última evaluación configurada en el sistema para asociar los enlaces
    evaluacion_activa = Evaluacion.objects.filter().last()
    if not evaluacion_activa:
        modeladmin.message_user(
            request, 
            "No se puede realizar el envío porque no hay ninguna evaluación activa configurada en el sistema.", 
            messages.ERROR
        )
        return

    # 3. Guardamos los IDs de los empleados seleccionados en la sesión
    empleados_ids = list(empleados_a_procesar.values_list('id', flat=True).distinct())
    
    session_key = f"envio_correos_{uuid.uuid4().hex}"
    request.session[session_key] = {
        'empleados_ids': empleados_ids,
        'evaluacion_id': evaluacion_activa.id_evaluacion, # Asociamos la evaluación activa por defecto
        'procesados': 0,
        'total': len(empleados_ids),
        'app_label': 'rh',
        'model_name': 'empleado',
    }

    return redirect(f"/admin/procesar-evaluaciones-loading/{session_key}/")

# 🌟 VISTA INTERMEDIA: PANTALLA DE CARGA DE FRUVER PROCESADA POR AJAX EN TIEMPO REAL
def procesar_evaluaciones_loading_view(request, session_key):
    data = request.session.get(session_key)
    if not data:
        return redirect('/admin/')

    # Si es una petición AJAX (Fetch), procesamos un lote de 3 correos para no saturar
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'ajax' in request.GET:
        ids_restantes = data['empleados_ids']
        total_a_procesar = min(3, len(ids_restantes)) # Lotes de 3 en 3
        lote = ids_restantes[:total_a_procesar]
        
        contador_local = 0
        dominio_sitio = request.build_absolute_uri('/')
        
        for emp_id in lote:
            try:
                empleado = Empleado.objects.get(id=emp_id)
                token = TokenAccesoEvaluacion.objects.create(empleado=empleado)
                url_acceso = f"{dominio_sitio}evaluacion/acceso/{token.id_token}/"
                
                asunto = "Acceso Exclusivo: Tu Evaluación de Desempeño"
                mensaje = f"Hola {empleado.nombre_largo if hasattr(empleado, 'nombre_largo') else empleado.nombre_largo},\n\n" \
                          f"Te compartimos tu enlace personalizado para ingresar al sistema de evaluaciones de desempeño.\n" \
                          f"A través de este enlace podrás realizar tu autoevaluación (si te corresponde) y/o evaluar a tu personal a cargo.\n\n" \
                          f"Haz clic en el siguiente enlace para ingresar directamente sin necesidad de contraseña:\n" \
                          f"{url_acceso}\n\n" \
                          f"Este enlace expirará en 5 días.\n\n" \
                          f"Saludos cordiales,\nRecursos Humanos."
                
                send_mail(
                    asunto, mensaje, 'l.rodriguez@fruver.com.mx',
                    [empleado.CorreoElectronico], fail_silently=False
                )
                contador_local += 1
            except Exception:
                pass
        
        # Actualizamos el estado de la sesión
        data['empleados_ids'] = ids_restantes[total_a_procesar:]
        data['procesados'] += total_a_procesar
        request.session[session_key] = data
        
        # Si terminamos todo, mandamos el mensaje final de éxito
        if len(data['empleados_ids']) == 0:
            messages.success(request, f"Se generaron los tokens y se enviaron {data['procesados']} correos exitosamente.")
            del request.session[session_key] # Limpiamos sesión
            
        return JsonResponse({
            'completado': len(data['empleados_ids']) == 0,
            'procesados': data['procesados'],
            'total': data['total'],
            'url_retorno': f"/admin/{data['app_label']}/{data['model_name']}/"
        })

    # Renderizado inicial de la Pantalla de Carga limpia (HTML Puro)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enviando Evaluaciones...</title>
        <style>
            body {{
                margin: 0; padding: 0; width: 100vw; height: 100vh;
                background-color: #f3f4f6;
                display: flex; justify-content: center; align-items: center;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            .card {{
                background: #ffffff; padding: 35px 50px; border-radius: 12px;
                box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); text-align: center;
                border: 1px solid #e5e7eb; max-width: 420px;
            }}
            .spinner {{
                animation: spin 1s linear infinite; margin: 0 auto 15px auto;
                width: 42px; height: 42px; color: #72a651;
            }}
            .progress-bar-container {{
                width: 100%; background-color: #e5e7eb; border-radius: 9999px; height: 8px; margin-top: 15px; overflow: hidden;
            }}
            .progress-bar {{
                width: 0%; height: 100%; background-color: #72a651; transition: width 0.3s ease;
            }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        </style>
    </head>
    <body>
        <div class="card">
            <svg class="spinner" fill="none" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" style="opacity: 0.25;"></circle>
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" style="opacity: 0.75;"></path>
            </svg>
            <h3 style="margin: 0 0 8px 0; font-size: 18px; font-weight: 600; color: #1f2937;">
                Enviando Enlaces de Evaluación
            </h3>
            <p id="status-text" style="margin: 0; font-size: 14px; color: #6b7280; line-height: 1.4;">
                Iniciando el envío seguro de correos...
            </p>
            <div class="progress-bar-container">
                <div id="progress" class="progress-bar"></div>
            </div>
        </div>

        <script>
            function realizarEnvio() {{
                fetch(window.location.pathname + "?ajax=1", {{
                    headers: {{ 'X-Requested-With': 'XMLHttpRequest' }}
                }})
                .then(res => res.json())
                .then(data => {{
                    let porcentaje = Math.round((data.procesados / data.total) * 100);
                    document.getElementById("progress").style.width = porcentaje + "%";
                    document.getElementById("status-text").innerText = "Enviados: " + data.procesados + " de " + data.total + " correos electrónicos...";
                    
                    if (data.completado) {{
                        window.location.href = data.url_retorno;
                    }} else {{
                        // Pequeño delay de 100ms para no saturar el servidor y continuar el bucle
                        setTimeout(realizarEnvio, 100);
                    }}
                }})
                .catch(() => {{
                    alert("Ocurrió un problema en el servidor al enviar los correos.");
                }});
            }}
            // Iniciar ciclo en cuanto carge la vista
            window.onload = realizarEnvio;
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_content)
#admin.site.register(Departamento, DepartamentoAdmin)
admin_site.register(Departamento, DepartamentoAdmin)


class DepartamentoEmpresaFilter(admin.RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        empresa_activa = request.session.get('empresa_activa') or request.session.get('empresa_id')
        if empresa_activa:
            pk_field = field.remote_field.model._meta.pk.name
            limit_choices_to = {
                'empresa_id': empresa_activa
            }
            # Filtrar departamentos pertenecientes a la empresa activa
            qs = field.remote_field.model.objects.filter(**limit_choices_to).order_by('descripcion')
            return [(getattr(obj, pk_field), str(obj)) for obj in qs]
        return super().field_choices(field, request, model_admin)

class PuestoEmpresaFilter(admin.RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        empresa_activa = request.session.get('empresa_activa') or request.session.get('empresa_id')
        if empresa_activa:
            pk_field = field.remote_field.model._meta.pk.name
            limit_choices_to = {
                'empresa_id': empresa_activa
            }
            qs = field.remote_field.model.objects.filter(**limit_choices_to).order_by('descripcion')
            return [(getattr(obj, pk_field), str(obj)) for obj in qs]
        return super().field_choices(field, request, model_admin)
def matriz_competencias_html(queryset, guardados_ids, url_agregar=''):
    """Competencias específicas del empleado: selector por clasificación, buscador y resumen de las seleccionadas.
    Todas las casillas se quedan en el formulario (solo se ocultan), así save_model sigue recibiendo competencias_check.
    Al final de cada clasificación se puede dar de alta una competencia nueva (url_agregar, por AJAX)."""
    from django.utils.html import escape
    grupos = {}
    for comp in queryset:
        nombre = comp.id_clasificacion.descripcion if comp.id_clasificacion else "Competencias Específicas Sueltas"
        grupos.setdefault(nombre, []).append(comp)

    opciones, bloques = [], []
    inicial = None
    for i, (nombre, comps) in enumerate(grupos.items()):
        id_clasif = comps[0].id_clasificacion_id or ''
        marcadas = sum(1 for c in comps if c.id_competencia in guardados_ids)
        if inicial is None and marcadas:
            inicial = i
        opciones.append(f'<option value="{i}" data-nombre="{escape(nombre)}">{escape(nombre)} ({marcadas}/{len(comps)})</option>')
        casillas = ''.join(
            f'<label class="cmp-item" data-texto="{escape(c.descripcion.lower())}">'
            f'<input type="checkbox" name="competencias_check" value="{c.id_competencia}" data-grupo="{i}"'
            f'{" checked" if c.id_competencia in guardados_ids else ""}>'
            f'<span>{escape(c.descripcion)}</span></label>'
            for c in comps)
        nueva = ''
        if url_agregar and id_clasif:
            nueva = (f'<div class="cmp-nueva" data-clasif="{id_clasif}">'
                     f'<input type="text" maxlength="1000" placeholder="Nueva competencia para {escape(nombre.capitalize())}…">'
                     f'<button type="button">+ Agregar</button><small></small></div>')
        bloques.append(f'<div class="cmp-grupo" data-grupo="{i}" data-nombre="{escape(nombre)}">'
                       f'<h3 class="cmp-grupo-titulo">📂 {escape(nombre)}</h3>{casillas}{nueva}</div>')
    inicial = 0 if inicial is None else inicial

    return f'''
<style>
  .cmp-box {{ --cmp-fondo:#f9fafb; --cmp-tarjeta:#fff; --cmp-borde:#e5e7eb; --cmp-texto:#374151; --cmp-tenue:#6b7280;
             --cmp-acento:#2563eb; --cmp-chip:#eff6ff; --cmp-chip-borde:#bfdbfe;
             width:100%; margin-top:2rem; clear:both; background:var(--cmp-fondo); border:1px solid var(--cmp-borde);
             border-radius:.5rem; padding:1.5rem; color:var(--cmp-texto); }}
  html.dark .cmp-box {{ --cmp-fondo:rgba(24,24,27,.4); --cmp-tarjeta:rgba(39,39,42,.4); --cmp-borde:#3f3f46; --cmp-texto:#d4d4d8;
             --cmp-tenue:#a1a1aa; --cmp-acento:#60a5fa; --cmp-chip:rgba(37,99,235,.15); --cmp-chip-borde:rgba(96,165,250,.4); }}
  .cmp-box h2 {{ font-size:1rem; font-weight:600; margin:0 0 .25rem; }}
  .cmp-box .cmp-ayuda {{ font-size:.875rem; color:var(--cmp-tenue); margin:0 0 1.25rem; }}
  .cmp-sel {{ background:var(--cmp-tarjeta); border:1px solid var(--cmp-borde); border-radius:.5rem; padding:.75rem 1rem; margin-bottom:1rem; }}
  .cmp-sel-titulo {{ display:flex; justify-content:space-between; align-items:center; font-size:.8rem; font-weight:600;
                     text-transform:uppercase; letter-spacing:.04em; color:var(--cmp-acento); margin-bottom:.5rem; }}
  .cmp-sel-titulo button {{ font-size:.75rem; text-transform:none; letter-spacing:0; color:var(--cmp-tenue); background:none; border:0; cursor:pointer; text-decoration:underline; }}
  .cmp-chips {{ display:flex; flex-wrap:wrap; gap:.4rem; max-height:9.5rem; overflow:auto; }}
  .cmp-chip {{ display:inline-flex; align-items:center; gap:.35rem; max-width:100%; font-size:.8rem; line-height:1.2;
               background:var(--cmp-chip); border:1px solid var(--cmp-chip-borde); border-radius:999px; padding:.25rem .3rem .25rem .7rem; }}
  .cmp-chip span {{ cursor:pointer; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:42rem; }}
  .cmp-chip button {{ border:0; background:none; cursor:pointer; color:var(--cmp-tenue); font-size:1rem; line-height:1; padding:0 .25rem; }}
  .cmp-chip button:hover {{ color:#dc2626; }}
  .cmp-vacio {{ font-size:.85rem; font-style:italic; color:var(--cmp-tenue); }}
  .cmp-barra {{ display:flex; flex-wrap:wrap; gap:.75rem; align-items:center; margin-bottom:.75rem; }}
  .cmp-barra label {{ font-size:.85rem; font-weight:600; }}
  .cmp-barra select, .cmp-barra input {{ font-size:.875rem; color:var(--cmp-texto); background:var(--cmp-tarjeta); border:1px solid var(--cmp-borde);
               border-radius:.375rem; padding:.45rem .6rem; }}
  .cmp-barra select {{ min-width:22rem; max-width:100%; }}
  .cmp-barra input {{ flex:1; min-width:14rem; }}
  .cmp-lista {{ max-height:28rem; overflow:auto; padding-right:.25rem; }}
  .cmp-grupo-titulo {{ font-size:.75rem; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:var(--cmp-acento);
               border-bottom:1px solid var(--cmp-borde); padding-bottom:.4rem; margin:.75rem 0 .5rem; }}
  .cmp-item {{ display:flex; align-items:center; gap:1rem; background:var(--cmp-tarjeta); border:1px solid var(--cmp-borde);
               border-radius:.375rem; padding:.6rem 1rem; margin-bottom:.4rem; cursor:pointer; font-size:.875rem; }}
  .cmp-item:hover {{ border-color:var(--cmp-acento); }}
  .cmp-item input {{ accent-color:#3b82f6; min-width:16px; height:16px; }}
  .cmp-item.cmp-resalta {{ outline:2px solid var(--cmp-acento); }}
  .cmp-nueva {{ display:flex; flex-wrap:wrap; gap:.5rem; align-items:center; border:1px dashed var(--cmp-acento); border-radius:.375rem;
               padding:.5rem .75rem; margin:.25rem 0 .4rem; }}
  .cmp-nueva input {{ flex:1; min-width:14rem; font-size:.875rem; color:var(--cmp-texto); background:var(--cmp-tarjeta);
               border:1px solid var(--cmp-borde); border-radius:.375rem; padding:.45rem .6rem; }}
  .cmp-nueva button {{ font-size:.85rem; font-weight:600; color:#fff; background:var(--cmp-acento); border:0; border-radius:.375rem;
               padding:.5rem .9rem; cursor:pointer; }}
  .cmp-nueva button:disabled {{ opacity:.6; cursor:wait; }}
  .cmp-nueva small {{ flex-basis:100%; font-size:.8rem; color:#dc2626; }}
  .cmp-nueva small:empty {{ display:none; }}
  .cmp-oculto {{ display:none !important; }}
  @media (max-width:640px) {{ .cmp-barra select {{ min-width:0; width:100%; }} }}
</style>
<div class="cmp-box" id="cmp-box">
  <h2>Asignación de Competencias Específicas</h2>
  <p class="cmp-ayuda">Elija una clasificación y palomee las competencias específicas del puesto o libres que formarán parte de la evaluación individual de este colaborador.</p>
  <div class="cmp-sel">
    <div class="cmp-sel-titulo"><span>Seleccionadas (<b id="cmp-total">0</b>)</span>
      <button type="button" id="cmp-ver-sel">Ver solo seleccionadas</button></div>
    <div class="cmp-chips" id="cmp-chips"></div>
  </div>
  <div class="cmp-barra">
    <label for="cmp-clasif">Clasificación</label>
    <select id="cmp-clasif">
      <option value="sel">— Solo seleccionadas —</option>
      <option value="todas">— Todas las clasificaciones —</option>
      {''.join(opciones)}
    </select>
    <input type="search" id="cmp-buscar" placeholder="Buscar competencia en todas las clasificaciones…">
  </div>
  <div class="cmp-lista" id="cmp-lista">{''.join(bloques)}<p class="cmp-vacio cmp-oculto" id="cmp-sin">No hay competencias que mostrar.</p></div>
</div>
<script>
(function () {{
  var caja = document.getElementById('cmp-box'), combo = document.getElementById('cmp-clasif'),
      buscar = document.getElementById('cmp-buscar'), chips = document.getElementById('cmp-chips'),
      sin = document.getElementById('cmp-sin');
  var grupos = caja.querySelectorAll('.cmp-grupo'), urlAgregar = '{url_agregar}';
  function casillas() {{ return caja.querySelectorAll('input[name="competencias_check"]'); }}
  combo.value = '{inicial}';

  function filtrar() {{
    var vista = combo.value, texto = buscar.value.trim().toLowerCase(), visibles = 0;
    grupos.forEach(function (g) {{
      var hay = 0;
      g.querySelectorAll('.cmp-item').forEach(function (it) {{
        var cb = it.querySelector('input'), ver;
        if (texto) ver = it.dataset.texto.indexOf(texto) >= 0;
        else if (vista === 'sel') ver = cb.checked;
        else ver = vista === 'todas' || vista === g.dataset.grupo;
        it.classList.toggle('cmp-oculto', !ver); if (ver) hay++;
      }});
      var nueva = g.querySelector('.cmp-nueva'), conAlta = !texto && (vista === 'todas' || vista === g.dataset.grupo);
      if (nueva) nueva.classList.toggle('cmp-oculto', !conAlta);
      g.classList.toggle('cmp-oculto', !hay && !conAlta); visibles += hay;
    }});
    sin.classList.toggle('cmp-oculto', visibles > 0);
  }}

  function resumen() {{
    var total = 0, porGrupo = {{}};
    chips.innerHTML = '';
    casillas().forEach(function (cb) {{
      if (!cb.checked) return;
      total++; porGrupo[cb.dataset.grupo] = (porGrupo[cb.dataset.grupo] || 0) + 1;
      var g = caja.querySelector('.cmp-grupo[data-grupo="' + cb.dataset.grupo + '"]');
      var chip = document.createElement('span'); chip.className = 'cmp-chip';
      var t = document.createElement('span'); t.textContent = cb.nextElementSibling.textContent;
      t.title = g.dataset.nombre + ' — clic para verla en su clasificación';
      t.onclick = function () {{ irA(cb); }};
      var x = document.createElement('button'); x.type = 'button'; x.textContent = '×'; x.title = 'Quitar';
      x.onclick = function () {{ cb.checked = false; cambio(); }};
      chip.appendChild(t); chip.appendChild(x); chips.appendChild(chip);
    }});
    if (!total) chips.innerHTML = '<span class="cmp-vacio">Este empleado aún no tiene competencias específicas seleccionadas.</span>';
    document.getElementById('cmp-total').textContent = total;
    combo.querySelectorAll('option[data-nombre]').forEach(function (o) {{
      var n = caja.querySelectorAll('.cmp-grupo[data-grupo="' + o.value + '"] .cmp-item').length;
      o.textContent = o.dataset.nombre + ' (' + (porGrupo[o.value] || 0) + '/' + n + ')';
    }});
  }}

  function irA(cb) {{
    buscar.value = ''; combo.value = cb.dataset.grupo; filtrar();
    var it = cb.closest('.cmp-item'); it.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
    it.classList.add('cmp-resalta'); setTimeout(function () {{ it.classList.remove('cmp-resalta'); }}, 1500);
  }}

  function cambio() {{ resumen(); if (combo.value === 'sel' && !buscar.value) filtrar(); }}

  caja.addEventListener('change', function (e) {{ if (e.target.name === 'competencias_check') resumen(); }});

  // Alta de una competencia nueva en la clasificación: se guarda en el catálogo y queda palomeada para el empleado
  function agregar(nueva) {{
    var txt = nueva.querySelector('input'), btn = nueva.querySelector('button'), msg = nueva.querySelector('small');
    var descripcion = txt.value.trim();
    msg.textContent = '';
    if (!descripcion) {{ msg.textContent = 'Escriba la descripción de la competencia.'; txt.focus(); return; }}
    var token = document.querySelector('input[name="csrfmiddlewaretoken"]');
    var datos = new FormData(); datos.append('clasificacion', nueva.dataset.clasif); datos.append('descripcion', descripcion);
    btn.disabled = true;
    fetch(urlAgregar, {{ method: 'POST', body: datos, credentials: 'same-origin',
                        headers: {{ 'X-CSRFToken': token ? token.value : '' }} }})
      .then(function (r) {{ return r.json().then(function (j) {{ return {{ ok: r.ok, j: j }}; }}); }})
      .then(function (res) {{
        if (!res.ok) throw new Error(res.j.error || 'No se pudo agregar.');
        var g = nueva.closest('.cmp-grupo');
        var cb = caja.querySelector('input[name="competencias_check"][value="' + res.j.id + '"]');
        if (!cb) {{
          var it = document.createElement('label'); it.className = 'cmp-item'; it.dataset.texto = res.j.descripcion.toLowerCase();
          cb = document.createElement('input'); cb.type = 'checkbox'; cb.name = 'competencias_check';
          cb.value = res.j.id; cb.dataset.grupo = g.dataset.grupo;
          var sp = document.createElement('span'); sp.textContent = res.j.descripcion;
          it.appendChild(cb); it.appendChild(sp); g.insertBefore(it, nueva);
        }}
        cb.checked = true; txt.value = '';
        resumen(); filtrar(); irA(cb);
        if (res.j.existia) msg.textContent = 'Esa competencia ya existía en la clasificación; quedó seleccionada.';
      }})
      .catch(function (e) {{ msg.textContent = e.message; }})
      .finally(function () {{ btn.disabled = false; }});
  }}
  caja.querySelectorAll('.cmp-nueva').forEach(function (nueva) {{
    nueva.querySelector('button').onclick = function () {{ agregar(nueva); }};
    nueva.querySelector('input').addEventListener('keydown', function (e) {{
      if (e.key === 'Enter') {{ e.preventDefault(); agregar(nueva); }}   // que Enter no envíe el formulario del empleado
    }});
  }});
  combo.addEventListener('change', function () {{ buscar.value = ''; filtrar(); }});
  buscar.addEventListener('input', filtrar);
  document.getElementById('cmp-ver-sel').onclick = function () {{ buscar.value = ''; combo.value = 'sel'; filtrar(); }};
  resumen(); filtrar();
}})();
</script>
'''


class EmpleadoAdmin(CatalogosOrdenadosAdmin, EmpresaFilterAdmin):
    form = EmpleadoAdminForm  
    model_class = Empleado
    pk_field_name = 'id_empleado'
    exclude = ('empresa',)  # 👈 Asegura que se excluya de la vista
    excel_columns = ['id_empleado', 'nombre_largo', 'id_puesto_id', 'id_departamento_id', 'CorreoElectronico', 'estado_empleado', 'fechaalta', 'se_evalua']
    list_display = ('id_empleado', 'nombre_largo', 'id_puesto', 'id_departamento', 'id_jefe', 'es_jefe_departamento', 'CorreoElectronico', 'estado_empleado', 'fechaalta', 'se_evalua', 'acciones_rh')
    # 🌟 APLICAR FILTROS PERSONALIZADOS AQUÍ:
    list_filter = (
        ('id_departamento', DepartamentoEmpresaFilter),
        ('id_puesto', PuestoEmpresaFilter),
        'es_jefe_departamento', 
        'CorreoElectronico', 
        'estado_empleado', 
        'se_evalua'
    )
    search_fields = ('nombre_largo', 'id_puesto__descripcion', 'CorreoElectronico', 'id_jefe__nombre_largo')

    # 🌟 ÚNICA DEFINICIÓN:
    action_form = CustomActionForm
    action_submit_label = "Ejecutar"

    inlines = []  
    actions = [enviar_enlaces_seleccionados]

    # 🌟 Sobrescribimos get_form_kwargs para que el admin de Django le pase 'request' al Formulario
    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)
        class ModelFormWithRequest(FormClass):
            def __new__(cls, *args, **form_kwargs):
                form_kwargs['request'] = request
                return FormClass(*args, **form_kwargs)
        return ModelFormWithRequest    

    # 🌟 AGREGA ESTE MÉTODO JUSTO AQUÍ ADENTRO:
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        matriz_html = ""
        
        if obj:
            # 1. Instanciamos tu formulario personalizado
            form = EmpleadoAdminForm(instance=obj)
            
            # 🌟 ACCIÓN CLAVE: Forzamos al campo interno a aceptar TODAS las competencias unificadas
            queryset = form.queryset_competencias_custom
            form.fields['competencias_seleccionadas'].queryset = queryset
            
            # 2. Obtenemos el set de IDs guardados utilizando la columna relacional física
            guardados_ids = set(EmpleadoCompetenciaAsignada.objects.filter(
                id_empleado_id=obj.pk
            ).values_list('id_competencia_id', flat=True))

            if queryset.exists():
                url_agregar = reverse(f'{self.admin_site.name}:rh_empleado_agregar_competencia', args=[obj.pk])
                matriz_html = matriz_competencias_html(queryset, guardados_ids, url_agregar)
            else:
                matriz_html = '<div class="mt-6 bg-gray-50 dark:bg-zinc-900/40 p-4 rounded-lg border border-gray-200 dark:border-zinc-800"><p class="text-sm italic text-gray-400">No hay competencias específicas configuradas para el puesto de este empleado.</p></div>'

        extra_context['matriz_competencias_html'] = mark_safe(matriz_html)
        
        # 🌟 PASO COMPLEMENTARIO OBLIGATORIO PARA UNFOLD:
        # Inyectamos el objeto de formulario procesado en el contexto para que reemplace al predeterminado
        extra_context['adminform'] = admin.helpers.AdminForm(
            form,
            list(self.get_fieldsets(request, obj)),
            self.get_prepopulated_fields(request, obj),
            self.get_readonly_fields(request, obj),
            model_admin=self
        )
        
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def get_urls(self):
        propias = [
            path('<path:object_id>/agregar-competencia/',
                 self.admin_site.admin_view(self.agregar_competencia_view),
                 name='rh_empleado_agregar_competencia'),
        ]
        return propias + super().get_urls()

    def agregar_competencia_view(self, request, object_id):
        """Da de alta (por AJAX) una competencia en el catálogo dentro de una clasificación del empleado.
        La asignación al empleado se guarda al darle Guardar, como las demás casillas."""
        if request.method != 'POST':
            return JsonResponse({'error': 'Método no permitido.'}, status=405)
        empleado = self.get_object(request, object_id)
        if empleado is None or not self.has_change_permission(request, empleado):
            return JsonResponse({'error': 'No tiene permiso para modificar este empleado.'}, status=403)

        descripcion = ' '.join((request.POST.get('descripcion') or '').split())
        clasif_id = request.POST.get('clasificacion') or ''
        if not descripcion:
            return JsonResponse({'error': 'Escriba la descripción de la competencia.'}, status=400)
        if not clasif_id.isdigit():
            return JsonResponse({'error': 'Clasificación no válida.'}, status=400)
        clasif_id = int(clasif_id)

        # Solo clasificaciones que ya se le muestran al empleado: las de su puesto o las de sus competencias guardadas
        permitidas = set(ClasificacionPorPuesto.objects.filter(
            id_puesto_id=empleado.id_puesto_id).values_list('id_clasificacion_id', flat=True))
        permitidas |= set(Competencia.objects.filter(
            empleadocompetenciaasignada__id_empleado_id=empleado.pk).values_list('id_clasificacion_id', flat=True))
        if clasif_id not in permitidas:
            return JsonResponse({'error': 'La clasificación no corresponde a este empleado.'}, status=400)

        existente = Competencia.objects.filter(id_clasificacion_id=clasif_id, descripcion__iexact=descripcion).first()
        if existente:
            return JsonResponse({'id': existente.pk, 'descripcion': existente.descripcion, 'existia': True})
        nueva = Competencia.objects.create(id_clasificacion_id=clasif_id, descripcion=descripcion)
        return JsonResponse({'id': nueva.pk, 'descripcion': nueva.descripcion, 'existia': False})

    def save_model(self, request, obj, form, change):

        if not obj.empresa_id:
            obj.empresa_id = request.session.get('empresa_id')

        super().save_model(request, obj, form, change)
        
        competencias_post = request.POST.getlist('competencias_check')
        competencias_post_ids = [int(pk) for pk in competencias_post if pk.isdigit()]

        # 1. Eliminar desmarcados
        EmpleadoCompetenciaAsignada.objects.filter(id_empleado=obj).exclude(id_competencia_id__in=competencias_post_ids).delete()

        # 2. Guardar nuevos checks marcados
        for comp_id in competencias_post_ids:
            EmpleadoCompetenciaAsignada.objects.get_or_create(id_empleado=obj, id_competencia_id=comp_id)

#admin.site.register(Empleado, EmpleadoAdmin)
admin_site.register(Empleado, EmpleadoAdmin)

class CompetenciaClasificacionAdmin(ExcelImportAdmin):
    model_class = CompetenciaClasificacion
    pk_field_name = 'id_clasificacion'
    excel_columns = ['descripcion', 'tipo']
    list_display = ('id_clasificacion', 'descripcion', 'tipo', 'acciones_rh')
    list_filter = ('descripcion', 'tipo')
    search_fields = ('descripcion',)
    fields = ('descripcion', 'tipo')
    inlines = [CompetenciaInline]

#admin.site.register(CompetenciaClasificacion, CompetenciaClasificacionAdmin)
admin_site.register(CompetenciaClasificacion, CompetenciaClasificacionAdmin)

class CompetenciaAdmin(CatalogosOrdenadosAdmin, ExcelImportAdmin):
    model_class = Competencia
    pk_field_name = 'id_competencia'
    excel_columns = ['id_clasificacion_id', 'descripcion']
    list_display = ('id_competencia', 'id_clasificacion', 'descripcion', 'acciones_rh')
    list_filter = ('descripcion',)  
    search_fields = ('descripcion',)

#admin.site.register(Competencia, CompetenciaAdmin)
admin_site.register(Competencia, CompetenciaAdmin)


class EvaluacionAdmin(EmpresaFilterAdmin):
    model_class = Evaluacion
    pk_field_name = 'id_evaluacion'
    excel_columns = ['descripcion', 'fecha_inicial', 'fecha_final']
    list_display = ('id_evaluacion', 'descripcion', 'fecha_inicial', 'fecha_final', 'acciones_rh', 'cerrada')
    search_fields = ('descripcion',)

    # 🌟 ÚNICA DEFINICIÓN:
    action_form = CustomActionForm
    action_submit_label = "Ejecutar"    
    actions = [enviar_enlaces_magicos]

#admin.site.register(Evaluacion, EvaluacionAdmin)
admin_site.register(Evaluacion, EvaluacionAdmin)
