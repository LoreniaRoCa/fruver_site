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
        'empresa_activa': empresa_obj
    }