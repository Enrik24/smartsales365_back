# ai_models/views.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
from datetime import datetime, timedelta
from django.db import connection
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import ModeloIA, PrediccionVentas
from .serializers import (ModeloIASerializer, PrediccionVentasSerializer,
                         EntrenamientoSerializer, PrediccionSolicitudSerializer)

class ModeloIAListView(generics.ListCreateAPIView):
    queryset = ModeloIA.objects.all()
    serializer_class = ModeloIASerializer
    permission_classes = [IsAdminUser]

class PrediccionVentasListView(generics.ListAPIView):
    serializer_class = PrediccionVentasSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PrediccionVentas.objects.select_related('modelo', 'categoria').all()

@api_view(['POST'])
@permission_classes([IsAdminUser])
def entrenar_modelo_ventas(request):
    serializer = EntrenamientoSerializer(data=request.data)
    if serializer.is_valid():
        datos = serializer.validated_data
        
        try:
            # Obtener datos históricos de ventas
            query = """
                SELECT DATE(p.fecha_pedido) as fecha, 
                       SUM(dp.cantidad * dp.precio_unitario_en_el_momento) as venta_total,
                       EXTRACT(MONTH FROM p.fecha_pedido) as mes,
                       EXTRACT(DAY FROM p.fecha_pedido) as dia,
                       EXTRACT(DOW FROM p.fecha_pedido) as dia_semana
                FROM pedidos p
                JOIN detalle_pedido dp ON p.id = dp.pedido_id
                WHERE p.fecha_pedido BETWEEN %s AND %s
                AND p.estado_pedido = 'entregado'
                GROUP BY DATE(p.fecha_pedido)
                ORDER BY fecha
            """
            
            with connection.cursor() as cursor:
                cursor.execute(query, [datos['fecha_inicio'], datos['fecha_fin']])
                resultados = cursor.fetchall()
                columnas = [col[0] for col in cursor.description]
            
            if len(resultados) < 30:  # Mínimo de datos para entrenar
                return Response(
                    {'error': 'Datos insuficientes para entrenar el modelo (mínimo 30 días)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Preparar datos para el modelo
            df = pd.DataFrame(resultados, columns=columnas)
            df['fecha'] = pd.to_datetime(df['fecha'])
            
            # Crear características
            df['dia_del_anio'] = df['fecha'].dt.dayofyear
            df['semana_del_anio'] = df['fecha'].dt.isocalendar().week
            df['es_fin_de_semana'] = (df['dia_semana'] >= 5).astype(int)
            
            # Preparar características y objetivo
            X = df[['mes', 'dia', 'dia_semana', 'dia_del_anio', 'semana_del_anio', 'es_fin_de_semana']]
            y = df['venta_total']
            
            # Dividir datos
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Entrenar modelo Random Forest
            modelo_rf = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                max_depth=10
            )
            modelo_rf.fit(X_train, y_train)
            
            # Evaluar modelo
            y_pred = modelo_rf.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            
            # Guardar modelo
            modelo_ia = ModeloIA.objects.create(
                nombre_modelo='Random Forest Ventas',
                version='1.0',
                fecha_entrenamiento=datetime.now(),
                parametros={
                    'n_estimators': 100,
                    'max_depth': 10,
                    'random_state': 42
                },
                precision=rmse,
                estado='entrenado'
            )
            
            # Guardar modelo serializado
            ruta_modelo = f'modelos/random_forest_ventas_{modelo_ia.id}.joblib'
            joblib.dump(modelo_rf, ruta_modelo)
            modelo_ia.ruta_modelo = ruta_modelo
            modelo_ia.save()
            
            return Response({
                'mensaje': 'Modelo entrenado exitosamente',
                'modelo_id': modelo_ia.id,
                'metricas': {
                    'RMSE': rmse,
                    'MAE': mae,
                    'MSE': mse
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_prediccion_ventas(request):
    serializer = PrediccionSolicitudSerializer(data=request.data)
    if serializer.is_valid():
        datos = serializer.validated_data
        
        try:
            modelo = ModeloIA.objects.get(id=datos['modelo_id'])
            
            # Cargar modelo entrenado
            modelo_rf = joblib.load(modelo.ruta_modelo)
            
            # Generar fechas para predicción
            fecha_inicio = datos['fecha_inicio']
            fecha_fin = datos['fecha_fin']
            
            fechas_prediccion = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
            
            # Preparar características para predicción
            caracteristicas = []
            for fecha in fechas_prediccion:
                carac = {
                    'mes': fecha.month,
                    'dia': fecha.day,
                    'dia_semana': fecha.weekday(),
                    'dia_del_anio': fecha.dayofyear,
                    'semana_del_anio': fecha.isocalendar().week,
                    'es_fin_de_semana': 1 if fecha.weekday() >= 5 else 0
                }
                caracteristicas.append(carac)
            
            df_pred = pd.DataFrame(caracteristicas)
            
            # Realizar predicciones
            predicciones = modelo_rf.predict(df_pred)
            
            # Crear resultado
            resultado = {}
            for i, fecha in enumerate(fechas_prediccion):
                resultado[fecha.strftime('%Y-%m-%d')] = float(predicciones[i])
            
            # Guardar predicción
            prediccion = PrediccionVentas.objects.create(
                modelo=modelo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                categoria_id=datos.get('categoria_id'),
                resultado_prediccion=resultado,
                metricas={
                    'predicciones_generadas': len(predicciones),
                    'rango_fechas': f"{fecha_inicio} a {fecha_fin}"
                }
            )
            
            return Response(PrediccionVentasSerializer(prediccion).data)
            
        except ModeloIA.DoesNotExist:
            return Response({'error': 'Modelo no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_metricas_ventas(request):
    """Obtener métricas básicas de ventas para el dashboard"""
    
    query_ventas_hoy = """
        SELECT COALESCE(SUM(monto_total), 0) 
        FROM pedidos 
        WHERE DATE(fecha_pedido) = CURRENT_DATE
        AND estado_pedido = 'entregado'
    """
    
    query_ventas_mes = """
        SELECT COALESCE(SUM(monto_total), 0) 
        FROM pedidos 
        WHERE EXTRACT(MONTH FROM fecha_pedido) = EXTRACT(MONTH FROM CURRENT_DATE)
        AND EXTRACT(YEAR FROM fecha_pedido) = EXTRACT(YEAR FROM CURRENT_DATE)
        AND estado_pedido = 'entregado'
    """
    
    query_pedidos_pendientes = """
        SELECT COUNT(*) 
        FROM pedidos 
        WHERE estado_pedido IN ('pendiente', 'confirmado', 'en_proceso')
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query_ventas_hoy)
        ventas_hoy = cursor.fetchone()[0]
        
        cursor.execute(query_ventas_mes)
        ventas_mes = cursor.fetchone()[0]
        
        cursor.execute(query_pedidos_pendientes)
        pedidos_pendientes = cursor.fetchone()[0]
    
    return Response({
        'ventas_hoy': ventas_hoy,
        'ventas_mes': ventas_mes,
        'pedidos_pendientes': pedidos_pendientes,
        'fecha_consulta': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
# =============================================================================
# AGREGAR VIEWS DE MODELOS_IA
# =============================================================================
@api_view(['POST'])
@permission_classes([IsAdminUser])
def actualizar_modelo(request, modelo_id):
    """Actualizar modelo IA"""
    nueva_ruta = request.data.get('ruta_modelo')
    nueva_version = request.data.get('version')
    
    if not nueva_ruta:
        return Response({'error': 'ruta_modelo es requerida'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        modelo = ModeloIA.objects.get(id=modelo_id)
        modelo.actualizar_modelo(nueva_ruta, nueva_version)
        return Response({'mensaje': 'Modelo actualizado correctamente'})
    except ModeloIA.DoesNotExist:
        return Response({'error': 'Modelo no encontrado'}, status=status.HTTP_404_NOT_FOUND)