# API Сервис заказа товаров для розничных сетей

Backend-часть сервиса заказа товаров, разработанная на Django REST Framework.

## Технологии
- Python 3.12
- Django 6.0
- Django REST Framework
- SQLite (для разработки)
- Token Authentication

## Установка и запуск

### 1. Клонировать репозиторий
```bash
git clone <ссылка на репозиторий>
cd Diplo_m
```

### 2. Создать виртуальное окружение
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 3. Установить зависимости
```bash
pip install -r requirements.txt
```

### 4. Настроить email в orders/settings.py
```python
EMAIL_HOST_USER = 'ваш_email@gmail.com'
EMAIL_HOST_PASSWORD = 'пароль_приложения'
```

### 5. Применить миграции
```bash
python manage.py migrate
```

### 6. Создать суперпользователя
```bash
python manage.py createsuperuser
```

### 7. Запустить сервер
```bash
python manage.py runserver
```

## API Endpoints

| Метод | URL | Описание | Авторизация |
|-------|-----|----------|-------------|
| POST | /api/v1/user/register/ | Регистрация | Нет |
| POST | /api/v1/user/login/ | Авторизация | Нет |
| GET/PATCH | /api/v1/user/account/ | Профиль | Да |
| GET | /api/v1/shops/ | Список магазинов | Нет |
| GET | /api/v1/categories/ | Категории | Нет |
| GET | /api/v1/products/ | Товары | Нет |
| GET | /api/v1/products/<id>/ | Товар детально | Нет |
| GET/POST/DELETE | /api/v1/basket/ | Корзина | Да |
| GET/POST | /api/v1/orders/ | Заказы | Да |
| GET/POST/DELETE | /api/v1/contacts/ | Адреса доставки | Да |
| POST | /api/v1/shop/update/ | Загрузка прайса (YAML) | Да (поставщик) |

## Формат YAML для загрузки товаров

```yaml
shop: Название магазина
categories:
  - id: 1
    name: Категория
goods:
  - id: 1
    category: 1
    name: Название товара
    price: 1000
    price_rrc: 1200
    quantity: 10
    parameters:
      Цвет: красный
```

## Администрирование
Админ-панель доступна по адресу: http://127.0.0.1:8000/admin/