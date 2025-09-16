from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F
from apps.pos.models import SaleItemLot, LotOverrideAudit
import csv
import json
from datetime import datetime, timedelta

@login_required
def pos_interface(request):
    """Vista principal del POS - Sistema de Ventas"""
    return render(request, 'pos/pos.html')

@login_required
def pos_history(request):
    """Vista del historial de ventas POS"""
    # Obtener parámetros de filtro
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Consulta base: agrupar por sale_id usando SaleItemLot
    sales_query = SaleItemLot.objects.values('sale_id').annotate(
        total_items=Count('id'),
        total_qty=Sum('qty_consumed'),
        sale_date=F('created_at__date'),
        seller=F('movement__created_by__username')
    ).order_by('-created_at')
    
    # Aplicar filtros
    if search:
        sales_query = sales_query.filter(
            Q(sale_id__icontains=search) | 
            Q(movement__created_by__username__icontains=search)
        )
    
    if date_from:
        sales_query = sales_query.filter(created_at__date__gte=date_from)
    
    if date_to:
        sales_query = sales_query.filter(created_at__date__lte=date_to)
    
    # Paginación
    paginator = Paginator(sales_query, 20)
    page_number = request.GET.get('page')
    sales = paginator.get_page(page_number)
    
    context = {
        'sales': sales,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'pos/history.html', context)

@login_required
def pos_sale_detail(request, sale_id):
    """Vista de detalle de una venta específica con información de lotes"""
    # Obtener items de la venta
    sale_items = SaleItemLot.objects.filter(
        sale_id=sale_id
    ).select_related('product', 'lot', 'movement__created_by').order_by('item_sequence')
    
    if not sale_items.exists():
        return render(request, 'pos/sale_not_found.html', {'sale_id': sale_id})
    
    # Obtener información de overrides si existen
    overrides = LotOverrideAudit.objects.filter(
        sale_id=sale_id
    ).select_related('product', 'lot_chosen', 'actor')
    
    # Calcular totales
    total_items = sale_items.count()
    total_qty = sale_items.aggregate(Sum('qty_consumed'))['qty_consumed__sum'] or 0
    
    # Información de la venta
    first_item = sale_items.first()
    sale_info = {
        'sale_id': sale_id,
        'date': first_item.created_at,
        'seller': first_item.movement.created_by.username,
        'total_items': total_items,
        'total_qty': total_qty,
    }
    
    context = {
        'sale_info': sale_info,
        'movements': sale_items,  # Mantenemos el nombre 'movements' para compatibilidad con el template
        'overrides': overrides,
    }
    
    return render(request, 'pos/sale_detail.html', context)

@login_required
def pos_sale_lots_csv(request, sale_id):
    """Exportar detalle de lotes de una venta a CSV"""
    # Obtener items de la venta
    sale_items = SaleItemLot.objects.filter(
        sale_id=sale_id
    ).select_related('product', 'lot', 'movement__created_by').order_by('item_sequence')
    
    if not sale_items.exists():
        return JsonResponse({'error': 'Venta no encontrada'}, status=404)
    
    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="venta_{sale_id}_lotes.csv"'
    
    writer = csv.writer(response)
    
    # Encabezados
    writer.writerow([
        'Producto',
        'Código Producto',
        'Lote',
        'Fecha Vencimiento',
        'Cantidad',
        'Costo Unitario',
        'Timestamp',
        'Vendedor'
    ])
    
    # Datos
    for item in sale_items:
        writer.writerow([
            item.product.name,
            item.product.code,
            item.lot.lot_code,
            item.lot.expiry_date.strftime('%Y-%m-%d') if item.lot.expiry_date else '',
            str(item.qty_consumed),
            str(item.lot.unit_cost),
            item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            item.movement.created_by.username
        ])
    
    return response
