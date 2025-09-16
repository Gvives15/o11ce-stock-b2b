from django.shortcuts import render

def alerts_panel(request):
    """Renderiza el panel de alertas (la data se trae con fetch desde la API)."""
    return render(request, "panel/alerts.html")
