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
    """
    Асинхронный импорт товаров из YAML.
    Вся бизнес-логика (проверка владельца магазина, транзакция,
    update_or_create вместо delete+create) вынесена в services.import_price_list —
    задача отвечает только за чтение файла, парсинг YAML и удаление временного файла.
    """
    import os
    from backend.models import User
    from backend.services import import_price_list, ServiceError

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return f'Ошибка импорта: пользователь id={user_id} не найден'

    if user.user_type != 'shop':
        return 'Ошибка импорта: импортировать прайс-лист может только пользователь типа "shop"'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return f'Ошибка импорта: некорректный YAML ({e})'
    finally:
        # временный файл больше не нужен независимо от результата парсинга
        if os.path.exists(file_path):
            os.remove(file_path)

    try:
        shop, goods_count = import_price_list(data, user)
    except ServiceError as e:
        return f'Ошибка импорта: {e.message}'
    except (KeyError, TypeError) as e:
        return f'Ошибка импорта: в YAML отсутствует обязательное поле {e}'

    return f'Импорт завершён: магазин "{shop.name}", {goods_count} позиций'