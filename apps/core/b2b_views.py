from django.shortcuts import render

def home(request):
    """Página principal B2B - catálogo de ofertas."""
    return render(request, "b2b/offers.html")

def cart(request):
    """Carrito de compras B2B."""
    return render(request, "b2b/cart.html")

def checkout(request):
    """Proceso de checkout B2B."""
    return render(request, "b2b/checkout.html")