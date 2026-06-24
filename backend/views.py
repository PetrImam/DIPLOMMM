from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
import yaml

from .models import Shop, Category, Product, ProductInfo, Order, OrderItem, Contact, Parameter, ProductParameter
from .serializers import (ShopSerializer, CategorySerializer, ProductInfoSerializer,
                          OrderSerializer, OrderItemSerializer, ContactSerializer, UserSerializer)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        required = ['email', 'password', 'first_name', 'last_name', 'username']
        for field in required:
            if not data.get(field):
                return Response({'error': f'Поле {field} обязательно'}, status=400)
        from .models import User
        if User.objects.filter(email=data['email']).exists():
            return Response({'error': 'Пользователь с таким email уже существует'}, status=400)
        user = User.objects.create_user(
            email=data['email'],
            username=data['username'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            company=data.get('company', ''),
            position=data.get('position', ''),
            user_type=data.get('user_type', 'buyer'),
        )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'email': user.email}, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({'error': 'Укажите email и пароль'}, status=400)
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'error': 'Неверный email или пароль'}, status=400)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'email': user.email})


class AccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ShopView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        shops = Shop.objects.filter(state=True)
        serializer = ShopSerializer(shops, many=True)
        return Response(serializer.data)


class CategoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


class ProductView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = ProductInfo.objects.select_related(
            'product', 'shop'
        ).prefetch_related('product_parameters__parameter')
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
        serializer = ProductInfoSerializer(queryset, many=True)
        return Response(serializer.data)


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            product_info = ProductInfo.objects.select_related(
                'product', 'shop'
            ).prefetch_related('product_parameters__parameter').get(pk=pk)
        except ProductInfo.DoesNotExist:
            return Response({'error': 'Товар не найден'}, status=404)
        serializer = ProductInfoSerializer(product_info)
        return Response(serializer.data)


class BasketView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        order = Order.objects.filter(user=request.user, status='basket').prefetch_related(
            'ordered_items__product_info__product',
            'ordered_items__product_info__shop',
        ).first()
        if not order:
            return Response({'ordered_items': [], 'total_sum': 0})
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def post(self, request):
        product_info_id = request.data.get('product_info_id')
        quantity = request.data.get('quantity', 1)
        if not product_info_id:
            return Response({'error': 'Укажите product_info_id'}, status=400)
        try:
            product_info = ProductInfo.objects.get(pk=product_info_id)
        except ProductInfo.DoesNotExist:
            return Response({'error': 'Товар не найден'}, status=404)
        if product_info.quantity < int(quantity):
            return Response({'error': 'Недостаточно товара на складе'}, status=400)
        order, _ = Order.objects.get_or_create(user=request.user, status='basket')
        item, created = OrderItem.objects.get_or_create(
            order=order, product_info=product_info,
            defaults={'quantity': quantity}
        )
        if not created:
            item.quantity += int(quantity)
            item.save()
        return Response({'success': 'Товар добавлен в корзину'})

    def delete(self, request):
        item_id = request.data.get('item_id')
        try:
            item = OrderItem.objects.get(pk=item_id, order__user=request.user, order__status='basket')
            item.delete()
            return Response({'success': 'Товар удалён из корзины'})
        except OrderItem.DoesNotExist:
            return Response({'error': 'Товар не найден в корзине'}, status=404)


class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product',
            'ordered_items__product_info__shop',
        )
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response({'error': 'Укажите contact_id'}, status=400)
        try:
            contact = Contact.objects.get(pk=contact_id, user=request.user)
        except Contact.DoesNotExist:
            return Response({'error': 'Контакт не найден'}, status=404)
        order = Order.objects.filter(user=request.user, status='basket').first()
        if not order or not order.ordered_items.exists():
            return Response({'error': 'Корзина пуста'}, status=400)
        order.status = 'new'
        order.contact = contact
        order.save()
        try:
            from .emails import send_order_confirmation, send_order_notification_to_admin
            send_order_confirmation(order)
            send_order_notification_to_admin(order)
        except Exception as e:
            print(f'Ошибка отправки email: {e}')
        return Response({'success': f'Заказ №{order.id} оформлен'})


class ContactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def delete(self, request):
        contact_id = request.data.get('id')
        try:
            contact = Contact.objects.get(pk=contact_id, user=request.user)
            contact.delete()
            return Response({'success': 'Адрес удалён'})
        except Contact.DoesNotExist:
            return Response({'error': 'Адрес не найден'}, status=404)


class PriceUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.user_type != 'shop':
            return Response({'error': 'Только для поставщиков'}, status=403)
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Файл не передан'}, status=400)
        import os
        file_path = f'tmp_{request.user.id}.yaml'
        with open(file_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        from .tasks import do_import
        do_import.delay(file_path, request.user.id)
        return Response({'success': 'Импорт запущен, товары появятся через несколько секунд'})


class ShopStateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != 'shop':
            return Response({'error': 'Только для поставщиков'}, status=403)
        try:
            shop = Shop.objects.get(user=request.user)
            return Response({'state': shop.state})
        except Shop.DoesNotExist:
            return Response({'error': 'Магазин не найден'}, status=404)

    def post(self, request):
        if request.user.user_type != 'shop':
            return Response({'error': 'Только для поставщиков'}, status=403)
        state = request.data.get('state')
        if state is None:
            return Response({'error': 'Укажите state'}, status=400)
        try:
            shop = Shop.objects.get(user=request.user)
            shop.state = state
            shop.save()
            return Response({'success': 'Статус обновлён'})
        except Shop.DoesNotExist:
            return Response({'error': 'Магазин не найден'}, status=404)


class ShopOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != 'shop':
            return Response({'error': 'Только для поставщиков'}, status=403)
        orders = Order.objects.filter(
            ordered_items__product_info__shop__user=request.user
        ).exclude(status='basket').prefetch_related(
            'ordered_items__product_info__product',
            'ordered_items__product_info__shop',
            'contact',
        ).distinct()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.user_type != 'shop':
            return Response({'error': 'Только для поставщиков'}, status=403)
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=404)
        new_status = request.data.get('status')
        valid_statuses = ['confirmed', 'assembled', 'sent', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return Response({'error': f'Допустимые статусы: {valid_statuses}'}, status=400)
        order.status = new_status
        order.save()
        return Response({'success': f'Статус заказа №{order.id} обновлён на "{new_status}"'})
