from .models import Empresa

def empresa_activa(request):
    """
    Inyecta la empresa seleccionada en el contexto global de las plantillas.
    """
    empresa_id = request.session.get('empresa_id')
    empresa_obj = None
    
    if empresa_id:
        empresa_obj = Empresa.objects.filter(id_empresa=empresa_id).first()
        
    return {
        'empresa_activa': empresa_obj,
        'inicio_modulo_url': inicio_modulo_url(request.path),
    }


# Mismas rutas con las que NavegacionDinamicaMiddleware reconoce el módulo de Recursos Humanos
RUTAS_RH = ['/admin/rh/', '/admin/vacaciones/', 'evaluacion', 'empleado', 'puesto', 'departamento', 'competencia', 'resumen', 'panel']


def inicio_modulo_url(path):
    """A dónde lleva el nombre del módulo (arriba a la izquierda): en RH, su tablero; en lo demás, todos los módulos."""
    path = (path or '').lower()
    return '/admin/rh/dashboard/' if any(k in path for k in RUTAS_RH) else '/admin/dashboard/'