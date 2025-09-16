from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from decimal import Decimal
import json

from apps.catalog.models import Product
from apps.stock.models import StockLot
from apps.orders.models import Order
from apps.customers.models import Customer
from apps.notifications.models import Notification
from .security import scope_required


@login_required
@scope_required('dashboard')
def dashboard(request):
    now = timezone.now()
    new_orders_24h = Order.objects.filter(created_at__gte=now - timezone.timedelta(hours=24)).count()
    on_hand_total = StockLot.objects.aggregate(total=Sum("qty_on_hand")).get("total") or Decimal("0")
    near_expiry_qs = StockLot.objects.filter(qty_on_hand__gt=0, expiry_date__lte=(now.date() + timezone.timedelta(days=30)))
    near_expiry_count = near_expiry_qs.count()
    near_expiry = near_expiry_qs.select_related("product").order_by("expiry_date")[:20]
    orders_total_7d = Order.objects.filter(created_at__gte=now - timezone.timedelta(days=7)).count()

    ctx = {
        "new_orders_24h": new_orders_24h,
        "on_hand_total": on_hand_total,
        "near_expiry_count": near_expiry_count,
        "orders_total_7d": orders_total_7d,
        "near_expiry": near_expiry,
    }
    return render(request, "panel/dashboard.html", ctx)


@login_required
@scope_required('inventory')
def stock_list(request):
    products = Product.objects.filter(is_active=True).order_by("name")[:500]
    rows = []
    for p in products:
        on_hand = StockLot.objects.filter(product=p).aggregate(total=Sum("qty_on_hand")).get("total") or Decimal("0")
        rows.append({"product": p, "on_hand": on_hand})
    return render(request, "panel/stock_list.html", {"rows": rows})


@login_required
@scope_required('orders')
def orders_list(request):
    orders = Order.objects.order_by("-created_at")[:50]
    return render(request, "panel/orders_list.html", {"orders": orders})


@login_required
def alerts_list(request):
    alerts = Notification.objects.order_by("-created_at")[:100]
    return render(request, "panel/alerts_list.html", {"alerts": alerts})


@login_required
@scope_required('customers')
def customers_list(request):
    customers = Customer.objects.order_by("name")[:200]
    return render(request, "panel/customers_list.html", {"customers": customers})


# Vistas de detalle
@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    stock_lots = StockLot.objects.filter(product=product).order_by('-created_at')
    total_stock = stock_lots.aggregate(total=Sum('qty_on_hand'))['total'] or 0
    
    ctx = {
        'product': product,
        'stock_lots': stock_lots,
        'total_stock': total_stock,
    }
    return render(request, 'panel/product_detail.html', ctx)


@login_required
@scope_required('orders')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
            order.status = new_status
            order.save()
            messages.success(request, f'Estado de la orden actualizado a {new_status}')
            return redirect('panel:order_detail', order_id=order.id)
    
    ctx = {
        'order': order,
    }
    return render(request, 'panel/order_detail.html', ctx)


@login_required
@scope_required('customers')
def customer_detail(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    recent_orders = Order.objects.filter(customer=customer).order_by('-created_at')[:10]
    total_orders = Order.objects.filter(customer=customer).count()
    
    ctx = {
        'customer': customer,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
    }
    return render(request, 'panel/customer_detail.html', ctx)


# Vistas de creación
@login_required
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        category = request.POST.get('category')
        price = request.POST.get('price')
        description = request.POST.get('description')
        
        if name and sku and price:
            try:
                product = Product.objects.create(
                    name=name,
                    sku=sku,
                    category=category or '',
                    price=Decimal(price),
                    description=description or '',
                    is_active=True
                )
                messages.success(request, f'Producto "{name}" creado exitosamente')
                return redirect('panel:product_detail', product_id=product.id)
            except Exception as e:
                messages.error(request, f'Error al crear el producto: {str(e)}')
        else:
            messages.error(request, 'Por favor completa todos los campos requeridos')
    
    return render(request, 'panel/add_product.html')


@login_required
def add_customer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        
        if name and email:
            try:
                customer = Customer.objects.create(
                    name=name,
                    email=email,
                    phone=phone or '',
                    address=address or '',
                    city=city or ''
                )
                messages.success(request, f'Cliente "{name}" creado exitosamente')
                return redirect('panel:customer_detail', customer_id=customer.id)
            except Exception as e:
                messages.error(request, f'Error al crear el cliente: {str(e)}')
        else:
            messages.error(request, 'Por favor completa todos los campos requeridos')
    
    return render(request, 'panel/add_customer.html')


# Vistas de edición
@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        if 'delete' in request.POST:
            product_name = product.name
            product.delete()
            messages.success(request, f'Producto "{product_name}" eliminado exitosamente')
            return redirect('panel:stock_list')
        else:
            product.name = request.POST.get('name', product.name)
            product.sku = request.POST.get('sku', product.sku)
            product.category = request.POST.get('category', product.category)
            product.price = Decimal(request.POST.get('price', product.price))
            product.description = request.POST.get('description', product.description)
            product.is_active = request.POST.get('is_active') == 'on'
            
            try:
                product.save()
                messages.success(request, f'Producto "{product.name}" actualizado exitosamente')
                return redirect('panel:product_detail', product_id=product.id)
            except Exception as e:
                messages.error(request, f'Error al actualizar el producto: {str(e)}')
    
    ctx = {'product': product}
    return render(request, 'panel/edit_product.html', ctx)


@login_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        if 'delete' in request.POST:
            customer_name = customer.name
            customer.delete()
            messages.success(request, f'Cliente "{customer_name}" eliminado exitosamente')
            return redirect('panel:customers_list')
        else:
            customer.name = request.POST.get('name', customer.name)
            customer.email = request.POST.get('email', customer.email)
            customer.phone = request.POST.get('phone', customer.phone)
            customer.address = request.POST.get('address', customer.address)
            customer.city = request.POST.get('city', customer.city)
            
            try:
                customer.save()
                messages.success(request, f'Cliente "{customer.name}" actualizado exitosamente')
                return redirect('panel:customer_detail', customer_id=customer.id)
            except Exception as e:
                messages.error(request, f'Error al actualizar el cliente: {str(e)}')
    
    ctx = {'customer': customer}
    return render(request, 'panel/edit_customer.html', ctx)


@login_required
def edit_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        if 'cancel' in request.POST:
            order.status = 'cancelled'
            order.save()
            messages.success(request, f'Orden #{order.id} cancelada exitosamente')
            return redirect('panel:order_detail', order_id=order.id)
        else:
            # Actualizar información de la orden
            order.status = request.POST.get('status', order.status)
            order.shipping_address = request.POST.get('shipping_address', order.shipping_address)
            order.notes = request.POST.get('notes', order.notes)
            
            try:
                order.save()
                messages.success(request, f'Orden #{order.id} actualizada exitosamente')
                return redirect('panel:order_detail', order_id=order.id)
            except Exception as e:
                messages.error(request, f'Error al actualizar la orden: {str(e)}')
    
    ctx = {'order': order}
    return render(request, 'panel/edit_order.html', ctx)


# Vistas de configuración
@login_required
def settings(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'general':
            # Manejar configuración general
            messages.success(request, 'Configuración general actualizada exitosamente')
        elif form_type == 'notifications':
            # Manejar configuración de notificaciones
            messages.success(request, 'Configuración de notificaciones actualizada exitosamente')
        elif form_type == 'security':
            # Manejar configuración de seguridad
            messages.success(request, 'Configuración de seguridad actualizada exitosamente')
        elif form_type == 'backup':
            # Manejar backup
            messages.success(request, 'Backup iniciado exitosamente')
        
        return redirect('panel:settings')
    
    return render(request, 'panel/settings.html')


@login_required
def user_profile(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'personal_info':
            # Actualizar información personal
            request.user.first_name = request.POST.get('first_name', request.user.first_name)
            request.user.last_name = request.POST.get('last_name', request.user.last_name)
            request.user.email = request.POST.get('email', request.user.email)
            
            try:
                request.user.save()
                messages.success(request, 'Información personal actualizada exitosamente')
            except Exception as e:
                messages.error(request, f'Error al actualizar la información: {str(e)}')
                
        elif form_type == 'change_password':
            # Cambiar contraseña
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada exitosamente')
            else:
                for error in form.errors.values():
                    messages.error(request, error[0])
                    
        elif form_type == 'preferences':
            # Actualizar preferencias
            messages.success(request, 'Preferencias actualizadas exitosamente')
        
        return redirect('panel:user_profile')
    
    return render(request, 'panel/user_profile.html')


# Vistas de reportes
@login_required
@scope_required('reports')
def reports(request):
    # Estadísticas para el dashboard de reportes
    total_sales = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = Order.objects.count()
    total_customers = Customer.objects.count()
    inventory_value = Product.objects.aggregate(
        total=Sum('price')
    )['total'] or 0
    
    ctx = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'inventory_value': inventory_value,
    }
    return render(request, 'panel/reports.html', ctx)


@login_required
@scope_required('analytics')
def analytics(request):
    # Estadísticas para analytics
    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = Order.objects.count()
    new_customers = Customer.objects.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()
    
    # Calcular tasa de conversión (simulada)
    conversion_rate = 3.2  # En una implementación real, esto se calcularía
    
    ctx = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'new_customers': new_customers,
        'conversion_rate': conversion_rate,
        'avg_order_value': 127.50,  # Simulado
        'customer_acquisition': 24,  # Simulado
    }
    return render(request, 'panel/analytics.html', ctx)


def custom_logout(request):
    logout(request)
    return redirect('panel:logout_success')


def logout_success(request):
    """Vista para mostrar la página de éxito después del logout"""
    return render(request, 'panel/logout_success.html')