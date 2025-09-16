from django.shortcuts import render

def stock_list(request):
    """Renderiza el panel de listado de stock (la data se trae con fetch desde la API)."""
    return render(request, "panel/stock_list.html")

def stock_detail(request, product_id):
    """Renderiza el panel de detalle de stock FEFO con entrada/salida rápidas."""
    return render(request, "panel/stock_detail.html", {"product_id": product_id})
