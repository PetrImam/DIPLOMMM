from django.urls import path
from .views import (
    RegisterView, LoginView, AccountView,
    ShopView, CategoryView, ProductView, ProductDetailView,
    BasketView, OrderView, ContactView, PriceUpdateView,
    ShopStateView, ShopOrdersView, OrderStatusView
)

urlpatterns = [
    # Авторизация
    path('user/register/', RegisterView.as_view(), name='register'),
    path('user/login/', LoginView.as_view(), name='login'),
    path('user/account/', AccountView.as_view(), name='account'),

    # Магазины и каталог
    path('shops/', ShopView.as_view(), name='shops'),
    path('categories/', CategoryView.as_view(), name='categories'),
    path('products/', ProductView.as_view(), name='products'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),

    # Корзина и заказы
    path('basket/', BasketView.as_view(), name='basket'),
    path('orders/', OrderView.as_view(), name='orders'),

    # Контакты
    path('contacts/', ContactView.as_view(), name='contacts'),

    # Для поставщиков
    path('shop/update/', PriceUpdateView.as_view(), name='price-update'),
    path('shop/state/', ShopStateView.as_view(), name='shop-state'),
    path('shop/orders/', ShopOrdersView.as_view(), name='shop-orders'),
    path('shop/orders/<int:pk>/status/', OrderStatusView.as_view(), name='order-status'),
]