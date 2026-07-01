"""
Сервисный слой приложения.

Здесь сосредоточена бизнес-логика, которая раньше была размазана по views.py.
Views остаются "тонкими": разбирают request, вызывают нужный сервис,
оборачивают результат в Response. Это упрощает тестирование (сервисы можно
тестировать без HTTP-слоя) и переиспользование логики (например, из Celery-задачи).

Все функции, которые могут бросить ошибку валидации, поднимают ServiceError
с понятным сообщением и http-статусом — views просто транслируют его в Response.
"""
from django.db import transaction

from .models import (
    Shop, Category, Product, ProductInfo, Parameter, ProductParameter,
    Order, OrderItem, Contact,
)


class ServiceError(Exception):
    """Ошибка бизнес-логики с HTTP-статусом для ответа клиенту."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# --------------------------------------------------------------------------
# Корзина
# --------------------------------------------------------------------------

def add_to_basket(user, product_info_id, quantity):
    if not product_info_id:
        raise ServiceError('Укажите product_info_id')
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise ServiceError('quantity должно быть целым числом')
    if quantity <= 0:
        raise ServiceError('quantity должно быть положительным числом')

    try:
        product_info = ProductInfo.objects.select_related('shop').get(pk=product_info_id)
    except ProductInfo.DoesNotExist:
        raise ServiceError('Товар не найден', status_code=404)

    if not product_info.shop.state:
        raise ServiceError('Магазин временно не принимает заказы')
    if product_info.quantity < quantity:
        raise ServiceError('Недостаточно товара на складе')

    with transaction.atomic():
        order, _ = Order.objects.get_or_create(user=user, status='basket')
        item, created = OrderItem.objects.select_for_update().get_or_create(
            order=order, product_info=product_info,
            defaults={'quantity': quantity},
        )
        if not created:
            new_quantity = item.quantity + quantity
            if product_info.quantity < new_quantity:
                raise ServiceError('Недостаточно товара на складе')
            item.quantity = new_quantity
            item.save()
    return order


def remove_from_basket(user, item_id):
    try:
        item = OrderItem.objects.get(pk=item_id, order__user=user, order__status='basket')
    except OrderItem.DoesNotExist:
        raise ServiceError('Товар не найден в корзине', status_code=404)
    item.delete()


# --------------------------------------------------------------------------
# Заказы
# --------------------------------------------------------------------------

def place_order(user, contact_id):
    """
    Переводит текущую корзину пользователя в статус 'new', закрепляя
    за ней адрес доставки. Возвращает оформленный заказ.
    """
    if not contact_id:
        raise ServiceError('Укажите contact_id')
    try:
        contact = Contact.objects.get(pk=contact_id, user=user)
    except Contact.DoesNotExist:
        raise ServiceError('Контакт не найден', status_code=404)

    with transaction.atomic():
        order = Order.objects.select_for_update().filter(user=user, status='basket').first()
        if not order or not order.ordered_items.exists():
            raise ServiceError('Корзина пуста')

        # Дополнительно проверяем, что на складе всё ещё достаточно остатков
        # на момент оформления (могло измениться с момента добавления в корзину).
        for item in order.ordered_items.select_related('product_info'):
            if item.product_info.quantity < item.quantity:
                raise ServiceError(
                    f'Недостаточно товара "{item.product_info.product.name}" на складе'
                )

        order.status = 'new'
        order.contact = contact
        order.save()

    return order


def update_order_status(order, new_status):
    valid_statuses = ['confirmed', 'assembled', 'sent', 'delivered', 'cancelled']
    if new_status not in valid_statuses:
        raise ServiceError(f'Допустимые статусы: {valid_statuses}')
    order.status = new_status
    order.save()
    return order


# --------------------------------------------------------------------------
# Импорт прайс-листа поставщиком
# --------------------------------------------------------------------------

def import_price_list(data, user):
    """
    Импортирует прайс-лист (уже распарсенный из YAML словарь) для магазина,
    принадлежащего переданному пользователю.

    Важные моменты, отличающие эту реализацию от наивной:

    1. Владелец магазина определяется ИСКЛЮЧИТЕЛЬНО полем Shop.user
       (текущий авторизованный пользователь), а не названием 'shop' из файла.
       Название из файла используется только для переименования СВОЕГО
       магазина — поставщик не может ни создать, ни перезаписать чужой
       магазин, просто подставив в YAML чужое имя.

    2. Импорт выполняется в одной транзакции (transaction.atomic). Если
       где-то в процессе случится ошибка (битые данные, нарушение
       ограничений и т.п.), все изменения откатятся, и магазин останется
       с прежним, валидным каталогом — а не пустым.

    3. Вместо "удалить всё, затем создать заново" используется
       update_or_create по уникальному ключу (product, shop, external_id):
       существующие позиции обновляются на месте, новые — создаются.
       Позиции, которых больше нет в свежем прайсе, удаляются отдельным
       шагом — но только после того, как весь файл успешно прочитан,
       так что частичный/ошибочный файл не обнулит каталог.
    """
    if not isinstance(data, dict) or 'shop' not in data:
        raise ServiceError('Некорректный формат YAML: отсутствует поле "shop"')

    goods = data.get('goods', [])
    categories_data = data.get('categories', [])

    with transaction.atomic():
        shop, _ = Shop.objects.get_or_create(
            user=user, defaults={'name': data['shop']}
        )
        if shop.name != data['shop']:
            shop.name = data['shop']
            shop.save(update_fields=['name'])

        for category_data in categories_data:
            category, _ = Category.objects.get_or_create(
                id=category_data['id'],
                defaults={'name': category_data['name']},
            )
            if category.name != category_data['name']:
                category.name = category_data['name']
                category.save(update_fields=['name'])
            category.shops.add(shop)

        seen_product_info_ids = []

        for item in goods:
            try:
                category = Category.objects.get(id=item['category'])
            except Category.DoesNotExist:
                raise ServiceError(
                    f'Категория с id={item["category"]} не описана в разделе "categories"'
                )

            product, _ = Product.objects.get_or_create(name=item['name'], category=category)

            product_info, _ = ProductInfo.objects.update_or_create(
                product=product, shop=shop, external_id=item['id'],
                defaults={
                    'model': item.get('model', ''),
                    'quantity': item['quantity'],
                    'price': item['price'],
                    'price_rrc': item['price_rrc'],
                },
            )
            seen_product_info_ids.append(product_info.id)

            # параметры товара — тоже update_or_create, без удаления всего набора
            incoming_param_names = set(item.get('parameters', {}).keys())
            for param_name, param_value in item.get('parameters', {}).items():
                parameter, _ = Parameter.objects.get_or_create(name=param_name)
                ProductParameter.objects.update_or_create(
                    product_info=product_info, parameter=parameter,
                    defaults={'value': str(param_value)},
                )
            # удаляем параметры, которых больше нет в свежем прайсе для этой позиции
            ProductParameter.objects.filter(
                product_info=product_info
            ).exclude(parameter__name__in=incoming_param_names).delete()

        # Позиции, которые были у магазина раньше, но отсутствуют в новом
        # прайсе (товар сняли с продажи) — удаляем. Делаем это в конце,
        # когда уже точно известно, что файл целиком корректен.
        ProductInfo.objects.filter(shop=shop).exclude(
            id__in=seen_product_info_ids
        ).delete()

    return shop, len(goods)
