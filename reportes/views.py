from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connection
import pandas as pd

@login_required
def inventario_pivot_view(request):
    try:
        query = """
            SELECT 
                v_nombre_cul AS "Cultivo",
                v_nombre_col AS "Color",
                v_nombre_eti AS "Etiqueta",
                v_nombre_prc AS "Variedad",
                v_nombre_tam AS "Tamaño",
                n_bulxpa_pal AS "Cantidad",
                d_empaque_pal AS "Fecha"
            FROM conc_eye_inventario
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            data = cursor.fetchall()

        df = pd.DataFrame(data, columns=columns)
        df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
        if 'Fecha' in df.columns:
            df['Fecha'] = df['Fecha'].astype(str)

        pivot_data = df.to_dict(orient='records')
    except Exception as e:
        print(f"Error cargando inventario: {e}")
        pivot_data = []

    return render(request, 'reportes/inventario_pivot.html', {'pivot_data': pivot_data})