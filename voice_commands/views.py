# voice_commands/views.py
import re
import json
import openai
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import ComandoVoz, ComandoTexto
from .serializers import (ComandoVozSerializer, ComandoTextoSerializer,
                         ProcesarComandoSerializer)
from analytics.views import generar_reporte

class ComandoVozListView(generics.ListAPIView):
    serializer_class = ComandoVozSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ComandoVoz.objects.filter(usuario=self.request.user).order_by('-fecha_ejecucion')

class ComandoTextoListView(generics.ListAPIView):
    serializer_class = ComandoTextoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ComandoTexto.objects.filter(usuario=self.request.user).order_by('-fecha_ejecucion')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def procesar_comando(request):
    serializer = ProcesarComandoSerializer(data=request.data)
    if serializer.is_valid():
        datos = serializer.validated_data
        inicio_procesamiento = datetime.now()
        
        try:
            # Determinar si es comando de voz o texto
            es_voz = 'transcript' in datos and datos['transcript']
            texto_entrada = datos.get('transcript') or datos.get('texto')
            contexto = datos.get('contexto', 'mobile_app')
            
            # Procesar el comando con OpenAI
            resultado = procesar_comando_openai(texto_entrada, contexto, request.user)
            
            # Calcular duración del procesamiento
            duracion = (datetime.now() - inicio_procesamiento).total_seconds()
            
            # Guardar el comando
            if es_voz:
                comando = ComandoVoz.objects.create(
                    usuario=request.user,
                    transcript_original=texto_entrada,
                    transcript_procesado=resultado.get('texto_procesado'),
                    tipo_comando=resultado.get('tipo_comando', 'reporte'),
                    contexto_aplicacion=contexto,
                    intencion_detectada=resultado.get('intencion'),
                    parametros_extraidos=resultado.get('parametros'),
                    duracion_procesamiento=duracion,
                    exito=resultado.get('exito', True),
                    respuesta_sistema=json.dumps(resultado.get('respuesta', {}))
                )
                serializer_class = ComandoVozSerializer
            else:
                comando = ComandoTexto.objects.create(
                    usuario=request.user,
                    texto_original=texto_entrada,
                    texto_procesado=resultado.get('texto_procesado'),
                    tipo_comando=resultado.get('tipo_comando', 'reporte'),
                    contexto_aplicacion=contexto,
                    intencion_detectada=resultado.get('intencion'),
                    parametros_extraidos=resultado.get('parametros'),
                    exito=resultado.get('exito', True),
                    respuesta_sistema=json.dumps(resultado.get('respuesta', {}))
                )
                serializer_class = ComandoTextoSerializer
            
            # Agregar ID del comando a la respuesta
            resultado['comando_id'] = comando.id
            
            return Response(resultado, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Guardar comando con error
            if es_voz:
                ComandoVoz.objects.create(
                    usuario=request.user,
                    transcript_original=texto_entrada,
                    tipo_comando='accion',
                    contexto_aplicacion=contexto,
                    exito=False,
                    respuesta_sistema=f"Error: {str(e)}"
                )
            else:
                ComandoTexto.objects.create(
                    usuario=request.user,
                    texto_original=texto_entrada,
                    tipo_comando='accion',
                    contexto_aplicacion=contexto,
                    exito=False,
                    respuesta_sistema=f"Error: {str(e)}"
                )
            
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def procesar_comando_openai(texto, contexto, usuario):
    """
    Procesa comandos en lenguaje natural usando OpenAI GPT
    """
    try:
        # Configurar OpenAI
        openai.api_key = settings.OPENAI_API_KEY
        
        # Crear prompt contextualizado
        prompt = crear_prompt_openai(texto, contexto, usuario)
        
        # Llamar a OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente especializado en análisis de datos y reportes para una plataforma de ecommerce llamada SmartSales365. Tu función es interpretar comandos de voz y texto para generar reportes, buscar información y ejecutar acciones específicas."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        # Procesar respuesta de OpenAI
        ai_response = response.choices[0].message.content.strip()
        
        # Parsear la respuesta JSON de OpenAI
        try:
            resultado = json.loads(ai_response)
        except json.JSONDecodeError:
            # Si no es JSON válido, usar procesamiento de respaldo
            resultado = procesar_comando_natural(texto, contexto, usuario)
            resultado['respuesta_ai'] = ai_response  # Incluir respuesta original de AI
        
        return resultado
        
    except Exception as e:
        # Fallback a procesamiento natural si OpenAI falla
        print(f"Error OpenAI: {e}")
        return procesar_comando_natural(texto, contexto, usuario)

def crear_prompt_openai(texto, contexto, usuario):
    """
    Crea un prompt estructurado para OpenAI
    """
    prompt = f"""
    ANALIZAR EL SIGUIENTE COMANDO Y RESPONDER EN FORMATO JSON:

    COMANDO: "{texto}"
    CONTEXTO: {contexto}
    USUARIO: {usuario.username}

    INSTRUCCIONES:
    1. Analiza la intención del usuario
    2. Identifica el tipo de acción requerida
    3. Extrae parámetros relevantes
    4. Genera una respuesta estructurada

    FORMATO DE RESPUESTA JSON:
    {{
        "exito": boolean,
        "intencion": "reporte_ventas|reporte_clientes|reporte_productos|busqueda|navegacion|accion_sistema",
        "tipo_comando": "reporte|busqueda|navegacion|accion",
        "texto_procesado": "texto interpretado",
        "parametros": {{
            "tipo_reporte": "ventas|clientes|productos|inventario",
            "formato": "pdf|excel|csv|pantalla",
            "fecha_inicio": "YYYY-MM-DD",
            "fecha_fin": "YYYY-MM-DD",
            "mes": "MM",
            "año": "YYYY",
            "categoria": "nombre_categoria",
            "producto": "nombre_producto",
            "ruta_destino": "/ruta/navegacion"
        }},
        "respuesta": {{
            "mensaje": "respuesta amigable al usuario",
            "accion_ejecutada": "descripción de la acción",
            "datos_disponibles": boolean
        }},
        "confianza": 0.0-1.0
    }}

    ACCIONES DISPONIBLES:
    - REPORTES: "ventas del mes", "clientes nuevos", "productos más vendidos", "inventario bajo"
    - BÚSQUEDAS: "buscar producto X", "encontrar clientes de Lima"
    - NAVEGACIÓN: "ir a pedidos", "ver mi perfil", "mostrar dashboard"

    EJEMPLOS:

    COMANDO: "Generar reporte de ventas de enero en PDF"
    RESPUESTA: {{
        "exito": true,
        "intencion": "reporte_ventas",
        "tipo_comando": "reporte",
        "texto_procesado": "Generar reporte de ventas del mes de enero en formato PDF",
        "parametros": {{
            "tipo_reporte": "ventas",
            "formato": "pdf",
            "mes": "01",
            "año": "2024"
        }},
        "respuesta": {{
            "mensaje": "Voy a generar el reporte de ventas de enero en formato PDF",
            "accion_ejecutada": "Iniciando generación de reporte",
            "datos_disponibles": true
        }},
        "confianza": 0.95
    }}

    COMANDO: "Mostrar productos con stock bajo"
    RESPUESTA: {{
        "exito": true,
        "intencion": "reporte_inventario",
        "tipo_comando": "reporte",
        "texto_procesado": "Generar reporte de productos con stock bajo",
        "parametros": {{
            "tipo_reporte": "inventario",
            "filtro_stock": "bajo"
        }},
        "respuesta": {{
            "mensaje": "Mostrando productos con stock bajo",
            "accion_ejecutada": "Filtrando productos por stock bajo",
            "datos_disponibles": true
        }},
        "confianza": 0.9
    }}

    COMANDO: "Buscar laptops gaming en oferta"
    RESPUESTA: {{
        "exito": true,
        "intencion": "busqueda_productos",
        "tipo_comando": "busqueda",
        "texto_procesado": "Buscar laptops gaming con descuentos",
        "parametros": {{
            "categoria": "laptops",
            "producto": "gaming",
            "filtro": "ofertas"
        }},
        "respuesta": {{
            "mensaje": "Buscando laptops gaming en oferta",
            "accion_ejecutada": "Ejecutando búsqueda en catálogo",
            "datos_disponibles": true
        }},
        "confianza": 0.88
    }}

    Responde SOLO con el JSON, sin texto adicional.
    """

    return prompt

def procesar_comando_natural(texto, contexto, usuario):
    """
    Procesamiento de respaldo sin OpenAI (usando expresiones regulares)
    """
    texto = texto.lower().strip()
    resultado = {
        'texto_original': texto,
        'texto_procesado': texto,
        'intencion': None,
        'parametros': {},
        'exito': True,
        'respuesta': {},
        'confianza': 0.7
    }
    
    # Extraer parámetros comunes
    parametros = extraer_parametros_comunes(texto)
    resultado['parametros'] = parametros
    
    # Detectar intención principal
    if any(palabra in texto for palabra in ['reporte', 'informe', 'estadística', 'estadisticas']):
        resultado['intencion'] = 'reporte_generico'
        resultado['tipo_comando'] = 'reporte'
        
        if 'ventas' in texto:
            resultado['intencion'] = 'reporte_ventas'
            resultado['parametros']['tipo_reporte'] = 'ventas'
        elif 'clientes' in texto or 'usuarios' in texto:
            resultado['intencion'] = 'reporte_clientes'
            resultado['parametros']['tipo_reporte'] = 'clientes'
        elif 'productos' in texto or 'inventario' in texto or 'stock' in texto:
            resultado['intencion'] = 'reporte_productos'
            resultado['parametros']['tipo_reporte'] = 'productos'
            
    elif any(palabra in texto for palabra in ['buscar', 'encontrar', 'mostrar']):
        resultado['intencion'] = 'busqueda_generica'
        resultado['tipo_comando'] = 'busqueda'
        
    elif any(palabra in texto for palabra in ['ir a', 'ver', 'mostrar', 'abrir']):
        resultado['intencion'] = 'navegacion'
        resultado['tipo_comando'] = 'navegacion'
    
    # Generar respuesta
    if resultado['intencion']:
        generar_respuesta_comando(resultado, usuario)
    else:
        resultado['exito'] = False
        resultado['respuesta'] = {
            'mensaje': 'No pude entender el comando. ¿Podrías reformularlo?',
            'accion_ejecutada': 'none',
            'datos_disponibles': False
        }
        resultado['confianza'] = 0.3
    
    return resultado

def extraer_parametros_comunes(texto):
    """Extrae parámetros comunes de los comandos"""
    parametros = {}
    
    # Extraer formato
    if 'pdf' in texto:
        parametros['formato'] = 'pdf'
    elif 'excel' in texto:
        parametros['formato'] = 'excel'
    elif 'csv' in texto:
        parametros['formato'] = 'csv'
    else:
        parametros['formato'] = 'pantalla'
    
    # Extraer tipo de reporte
    if 'ventas' in texto:
        parametros['tipo_reporte'] = 'ventas'
    elif 'clientes' in texto:
        parametros['tipo_reporte'] = 'clientes'
    elif 'productos' in texto:
        parametros['tipo_reporte'] = 'productos'
    elif 'inventario' in texto or 'stock' in texto:
        parametros['tipo_reporte'] = 'inventario'
    
    # Extraer meses
    meses = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }
    
    for mes_nombre, mes_numero in meses.items():
        if mes_nombre in texto:
            parametros['mes'] = mes_numero
            parametros['mes_nombre'] = mes_nombre.capitalize()
            break
    
    # Extraer años
    import re
    años = re.findall(r'20\d{2}', texto)
    if años:
        parametros['año'] = años[0]
    
    # Extraer fechas (patrón dd/mm/aaaa)
    fechas = re.findall(r'(\d{1,2}/\d{1,2}/20\d{2})', texto)
    if len(fechas) >= 2:
        parametros['fecha_inicio'] = fechas[0]
        parametros['fecha_fin'] = fechas[1]
    elif len(fechas) == 1:
        parametros['fecha'] = fechas[0]
    
    # Extraer productos o categorías específicas
    if 'laptop' in texto or 'computadora' in texto:
        parametros['categoria'] = 'laptops'
    elif 'teléfono' in texto or 'celular' in texto:
        parametros['categoria'] = 'smartphones'
    elif 'oferta' in texto or 'descuento' in texto:
        parametros['filtro'] = 'ofertas'
    
    return parametros

def generar_respuesta_comando(resultado, usuario):
    """Genera respuesta basada en el comando procesado"""
    intencion = resultado['intencion']
    parametros = resultado['parametros']
    
    mensajes = {
        'reporte_ventas': f"Generando reporte de ventas",
        'reporte_clientes': "Preparando análisis de clientes",
        'reporte_productos': "Compilando datos de productos",
        'reporte_inventario': "Analizando niveles de inventario",
        'busqueda_generica': "Realizando búsqueda solicitada",
        'navegacion': "Navegando a la sección indicada"
    }
    
    resultado['respuesta'] = {
        'mensaje': mensajes.get(intencion, "Ejecutando comando"),
        'accion_ejecutada': f"Procesando {intencion}",
        'datos_disponibles': True,
        'parametros_utilizados': parametros
    }

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_comandos_frecuentes(request):
    """Devuelve comandos frecuentes para sugerencias"""
    comandos_sugeridos = [
        {
            'comando': 'Generar reporte de ventas del mes actual en PDF',
            'descripcion': 'Crea un reporte de ventas del mes actual en formato PDF',
            'categoria': 'reportes'
        },
        {
            'comando': 'Mostrar productos con bajo stock',
            'descripcion': 'Lista productos con stock por debajo del mínimo',
            'categoria': 'inventario'
        },
        {
            'comando': 'Reporte de clientes nuevos del trimestre en Excel',
            'descripcion': 'Genera reporte de clientes registrados en los últimos 3 meses',
            'categoria': 'reportes'
        },
        {
            'comando': 'Buscar laptops gaming en oferta',
            'descripcion': 'Busca productos por nombre o descripción',
            'categoria': 'busqueda'
        },
        {
            'comando': 'Ventas de la última semana',
            'descripcion': 'Muestra el resumen de ventas de los últimos 7 días',
            'categoria': 'reportes'
        },
        {
            'comando': 'Productos más vendidos este mes',
            'descripcion': 'Lista los productos con mayores ventas del mes',
            'categoria': 'analytics'
        }
    ]
    
    return Response(comandos_sugeridos)

# Nuevo endpoint específico para OpenAI
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def procesar_comando_openai_endpoint(request):
    """Endpoint específico para procesamiento con OpenAI"""
    try:
        texto = request.data.get('command', '')
        contexto = request.data.get('context', 'mobile_app')
        
        if not texto:
            return Response({'error': 'Comando vacío'}, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = procesar_comando_openai(texto, contexto, request.user)
        
        return Response(resultado, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Error procesando comando con AI: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )