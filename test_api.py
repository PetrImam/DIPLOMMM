import requests

BASE_URL = 'http://127.0.0.1:8000/api/v1'

# 1. Регистрация поставщика
print('=== Регистрация поставщика ===')
response = requests.post(f'{BASE_URL}/user/register/', json={
    'email': 'shop@test.com',
    'username': 'shop_user',
    'password': 'testpass123',
    'first_name': 'Иван',
    'last_name': 'Петров',
    'user_type': 'shop',
})
print(response.json())
shop_token = response.json().get('token')

# 2. Регистрация покупателя
print('\n=== Регистрация покупателя ===')
response = requests.post(f'{BASE_URL}/user/register/', json={
    'email': 'buyer@test.com',
    'username': 'buyer_user',
    'password': 'testpass123',
    'first_name': 'Анна',
    'last_name': 'Сидорова',
    'user_type': 'buyer',
})
print(response.json())
buyer_token = response.json().get('token')

# 3. Загрузка прайса поставщиком
print('\n=== Загрузка прайса ===')
with open('shop1.yaml', 'rb') as f:
    response = requests.post(
        f'{BASE_URL}/shop/update/',
        files={'file': f},
        headers={'Authorization': f'Token {shop_token}'}
    )
print(response.json())

# 4. Список магазинов
print('\n=== Список магазинов ===')
response = requests.get(f'{BASE_URL}/shops/')
print(response.json())

# 5. Список категорий
print('\n=== Категории ===')
response = requests.get(f'{BASE_URL}/categories/')
print(response.json())

# 6. Список товаров
print('\n=== Товары ===')
response = requests.get(f'{BASE_URL}/products/')
data = response.json()
print(f'Найдено товаров: {len(data)}')
for item in data:
    print(f"  - {item['product']['name']} | цена: {item['price']} | кол-во: {item['quantity']}")

# 7. Добавить адрес доставки
print('\n=== Добавление адреса доставки ===')
response = requests.post(f'{BASE_URL}/contacts/', json={
    'city': 'Москва',
    'street': 'Ленина',
    'house': '10',
    'apartment': '5',
    'phone': '+79001234567',
}, headers={'Authorization': f'Token {buyer_token}'})
print(response.json())
contact_id = response.json().get('id')

# 8. Добавить товар в корзину
print('\n=== Добавление в корзину ===')
response = requests.post(f'{BASE_URL}/basket/', json={
    'product_info_id': 1,
    'quantity': 2,
}, headers={'Authorization': f'Token {buyer_token}'})
print(response.json())

# 9. Корзина
print('\n=== Корзина ===')
response = requests.get(f'{BASE_URL}/basket/',
    headers={'Authorization': f'Token {buyer_token}'})
print(response.json())

# 10. Оформить заказ
print('\n=== Оформление заказа ===')
response = requests.post(f'{BASE_URL}/orders/', json={
    'contact_id': contact_id,
}, headers={'Authorization': f'Token {buyer_token}'})
print(response.json())

# 11. Список заказов
print('\n=== Мои заказы ===')
response = requests.get(f'{BASE_URL}/orders/',
    headers={'Authorization': f'Token {buyer_token}'})
print(response.json())