# voice_commands/views.py
import re
import json
from datetime import datetime, timedelta
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
            contexto = datos.get('contexto', 'reports')
            
            # Procesar el comando
            resultado = procesar_comando_natural(texto_entrada, contexto, request.user)
            
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

def procesar_comando_natural(texto, contexto, usuario):
    """
    Procesa comandos en lenguaje natural usando expresiones regulares
    """
    texto = texto.lower().strip()
    resultado = {
        'texto_original': texto,
        'texto_procesado': texto,
        'intencion': None,
        'parametros': {},
        'exito': True,
        'respuesta': {},
        'accion_ejecutada': None
    }
    
    # Patrones para reportes
    patrones_reportes = {
        'reporte_ventas_mes': r'reporte.*ventas.*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
        'reporte_ventas_rango': r'reporte.*ventas.*(\d{1,2}/\d{1,2}/\d{4}).*(\d{1,2}/\d{1,2}/\d{4})',
        'reporte_clientes': r'reporte.*clientes',
        'reporte_productos': r'reporte.*productos',
        'reporte_pdf': r'reporte.*pdf',
        'reporte_excel': r'reporte.*excel',
    }
    
    # Patrones para búsquedas
    patrones_busqueda = {
        'buscar_producto': r'buscar.*producto.*"([^"]+)"',
        'buscar_cliente': r'buscar.*cliente.*"([^"]+)"',
        'ver_stock': r'stock.*producto',
    }
    
    # Extraer parámetros comunes
    parametros = extraer_parametros_comunes(texto)
    resultado['parametros'] = parametros
    
    # Determinar intención basada en patrones
    if contexto == 'reports':
        for intencion, patron in patrones_reportes.items():
            if re.search(patron, texto):
                resultado['intencion'] = intencion
                resultado['tipo_comando'] = 'reporte'
                break
        
        # Si no se detectó patrón específico, buscar palabras clave
        if not resultado['intencion']:
            if any(palabra in texto for palabra in ['reporte', 'informe', 'estadística']):
                resultado['intencion'] = 'reporte_generico'
                resultado['tipo_comando'] = 'reporte'
        
        # Ejecutar acción si es un reporte
        if resultado['intencion'] and 'reporte' in resultado['intencion']:
            ejecutar_reporte_comando(resultado, usuario)
    
    elif contexto == 'products':
        for intencion, patron in patrones_busqueda.items():
            if re.search(patron, texto):
                resultado['intencion'] = intencion
                resultado['tipo_comando'] = 'busqueda'
                break
    
    # Si no se detectó intención específica
    if not resultado['intencion']:
        resultado['intencion'] = 'no_reconocida'
        resultado['exito'] = False
        resultado['respuesta'] = {'mensaje': 'No pude entender el comando. ¿Podrías reformularlo?'}
    
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
    
    # Extraer tipo de reporte
    if 'ventas' in texto:
        parametros['tipo_reporte'] = 'ventas'
    elif 'clientes' in texto:
        parametros['tipo_reporte'] = 'clientes'
    elif 'productos' in texto:
        parametros['tipo_reporte'] = 'productos'
    
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
    
    # Extraer fechas (patrón dd/mm/aaaa)
    fechas = re.findall(r'(\d{1,2}/\d{1,2}/\d{4})', texto)
    if len(fechas) >= 2:
        parametros['fecha_inicio'] = fechas[0]
        parametros['fecha_fin'] = fechas[1]
    elif len(fechas) == 1:
        parametros['fecha'] = fechas[0]
    
    return parametros

def ejecutar_reporte_comando(resultado, usuario):
    """Ejecuta la generación de reporte basado en el comando"""
    parametros = resultado['parametros']
    
    # Mapear parámetros a formato de reporte
    datos_reporte = {
        'tipo_reporte': parametros.get('tipo_reporte', 'ventas'),
        'formato_salida': parametros.get('formato', 'pdf')
    }
    
    # Procesar fechas
    if 'fecha_inicio' in parametros and 'fecha_fin' in parametros:
        datos_reporte['fecha_inicio'] = parametros['fecha_inicio']
        datos_reporte['fecha_fin'] = parametros['fecha_fin']
    elif 'mes' in parametros:
        # Establecer rango del mes
        from datetime import datetime
        año_actual = datetime.now().year
        fecha_inicio = f"{año_actual}-{parametros['mes']}-01"
        # Calcular último día del mes
        if parametros['mes'] in ['04', '06', '09', '11']:
            ultimo_dia = '30'
        elif parametros['mes'] == '02':
            # Febrero (simplificado)
            ultimo_dia = '28'
        else:
            ultimo_dia = '31'
        fecha_fin = f"{año_actual}-{parametros['mes']}-{ultimo_dia}"
        datos_reporte['fecha_inicio'] = fecha_inicio
        datos_reporte['fecha_fin'] = fecha_fin
    
    # Aquí se integraría con el sistema de reportes
    # Por ahora, simulamos la respuesta
    resultado['respuesta'] = {
        'mensaje': f"Reporte de {datos_reporte['tipo_reporte']} generado exitosamente",
        'tipo': datos_reporte['tipo_reporte'],
        'formato': datos_reporte['formato_salida'],
        'parametros': datos_reporte
    }
    resultado['accion_ejecutada'] = 'generar_reporte'

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
            'comando': 'Buscar producto "refrigerador samsung"',
            'descripcion': 'Busca productos por nombre o descripción',
            'categoria': 'busqueda'
        }
    ]
    
    return Response(comandos_sugeridos)