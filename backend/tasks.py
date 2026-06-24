from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import yaml


@shared_task
def send_email(subject, message, recipient_list):
    """Асинхронная отправка email"""
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
    )
    return f'Email отправлен на {recipient_list}'


@shared_task
def do_import(file_path, user_id):
    """Асинхронный импорт товаров из YAML"""
    from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        shop, _ = Shop.objects.get_or_create(user=user, defaults={'name': data.get('shop', '')})
        shop.name = data.get('shop', shop.name)
        shop.save()

        for category_data in data.get('categories', []):
            category, _ = Category.objects.get_or_create(
                id=category_data['id'],
                defaults={'name': category_data['name']}
            )
            category.shops.add(shop)

        ProductInfo.objects.filter(shop=shop).delete()

        for item in data.get('goods', []):
            category = Category.objects.get(id=item['category'])
            product, _ = Product.objects.get_or_create(name=item['name'], category=category)

            product_info = ProductInfo.objects.create(
                product=product,
                shop=shop,
                external_id=item['id'],
                model=item.get('model', ''),
                quantity=item['quantity'],
                price=item['price'],
                price_rrc=item['price_rrc'],
            )

            for param_name, param_value in item.get('parameters', {}).items():
                parameter, _ = Parameter.objects.get_or_create(name=param_name)
                ProductParameter.objects.create(
                    product_info=product_info,
                    parameter=parameter,
                    value=str(param_value),
                )

        return f'Импорт завершён: {len(data.get("goods", []))} товаров'

    except Exception as e:
        return f'Ошибка импорта: {str(e)}'