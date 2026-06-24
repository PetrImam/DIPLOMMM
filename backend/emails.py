from django.core.mail import send_mail
from django.conf import settings


def send_order_confirmation(order):
    """Письмо покупателю при оформлении заказа"""
    items_text = '\n'.join([
        f"- {item.product_info.product.name} x{item.quantity} = {item.quantity * item.product_info.price} руб."
        for item in order.ordered_items.all()
    ])
    total = sum(item.quantity * item.product_info.price for item in order.ordered_items.all())

    send_mail(
        subject=f'Заказ №{order.id} принят',
        message=f'''Здравствуйте, {order.user.first_name}!

Ваш заказ №{order.id} успешно оформлен.

Состав заказа:
{items_text}

Итого: {total} руб.

Адрес доставки: {order.contact.city}, ул. {order.contact.street}, д. {order.contact.house}

Спасибо за покупку!''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        fail_silently=False,
    )


def send_order_notification_to_admin(order):
    """Письмо администратору при новом заказе"""
    items_text = '\n'.join([
        f"- {item.product_info.product.name} (магазин: {item.product_info.shop.name}) x{item.quantity}"
        for item in order.ordered_items.all()
    ])
    total = sum(item.quantity * item.product_info.price for item in order.ordered_items.all())

    send_mail(
        subject=f'Новый заказ №{order.id}',
        message=f'''Новый заказ от {order.user.email}

Покупатель: {order.user.first_name} {order.user.last_name}
Телефон: {order.contact.phone}
Адрес: {order.contact.city}, ул. {order.contact.street}, д. {order.contact.house}

Состав заказа:
{items_text}

Итого: {total} руб.''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.EMAIL_HOST_USER],
        fail_silently=False,
    )