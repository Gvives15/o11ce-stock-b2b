from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import views_users
from . import views_search
from . import views_ops

app_name = 'panel'

urlpatterns = [
    # Autenticación
    path("login/", auth_views.LoginView.as_view(template_name="panel/login.html"), name="login"),
    path("logout/", views.custom_logout, name="logout"),
    path("logout-success/", views.logout_success, name="logout_success"),

    # Dashboard y listas principales
    path("", views.dashboard, name="dashboard"),
    path("stock/", views.stock_list, name="stock_list"),
    path("orders/", views.orders_list, name="orders_list"),
    path("alerts/", views.alerts_list, name="alerts_list"),
    path("customers/", views.customers_list, name="customers_list"),
    
    # Páginas de detalle
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),
    path("order/<int:order_id>/", views.order_detail, name="order_detail"),
    path("customer/<int:customer_id>/", views.customer_detail, name="customer_detail"),
    
    # Formularios de creación
    path("product/add/", views.add_product, name="add_product"),
    path("customer/add/", views.add_customer, name="add_customer"),
    
    # Formularios de edición
    path("product/<int:product_id>/edit/", views.edit_product, name="edit_product"),
    path("customer/<int:customer_id>/edit/", views.edit_customer, name="edit_customer"),
    path("order/<int:order_id>/edit/", views.edit_order, name="edit_order"),
    
    # Configuración y perfil
    path("settings/", views.settings, name="settings"),
    path("profile/", views.user_profile, name="user_profile"),
    
    # Reportes y analytics
    path("reports/", views.reports, name="reports"),
    path("analytics/", views.analytics, name="analytics"),
    
    # Gestión de usuarios
    path("users/", views_users.users_list, name="users_list"),
    path("users/create/", views_users.user_create, name="user_create"),
    path("users/<int:user_id>/", views_users.user_detail, name="user_detail"),
    path("users/<int:user_id>/edit/", views_users.user_edit, name="user_edit"),
    path("users/<int:user_id>/toggle-active/", views_users.user_toggle_active, name="user_toggle_active"),
    path("users/<int:user_id>/roles/", views_users.user_roles_api, name="user_roles_api"),
    
    # Búsqueda global
    path("search/", views_search.global_search, name="global_search"),
    path("search/suggestions/", views_search.search_suggestions, name="search_suggestions"),
    
    # Feed de operaciones
    path("ops/", views_ops.ops_feed, name="ops_feed"),
    
    # Alias para compatibilidad
    path("inventory/", views.stock_list, name="inventory_list"),
    path("inventory/<int:product_id>/", views.product_detail, name="inventory_detail"),
    path("stock/<int:product_id>/", views.product_detail, name="stock_detail"),
]