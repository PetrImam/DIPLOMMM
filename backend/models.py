from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Пользователь"""
    USER_TYPE_CHOICES = (
        ('shop', 'Магазин'),
        ('buyer', 'Покупатель'),
    )
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=40, blank=True)
    position = models.CharField(max_length=40, blank=True)
    user_type = models.CharField(max_length=5, choices=USER_TYPE_CHOICES, default='buyer')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email


class Shop(models.Model):
    """Магазин/поставщик"""
    name = models.CharField(max_length=50)
    url = models.URLField(blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop', blank=True, null=True)
    state = models.BooleanField(default=True)  # принимает ли заказы

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'

    def __str__(self):
        return self.name


class Category(models.Model):
    """Категория товаров"""
    name = models.CharField(max_length=40)
    shops = models.ManyToManyField(Shop, related_name='categories', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар"""
    name = models.CharField(max_length=80)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """Информация о товаре у конкретного поставщика"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_infos')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='product_infos')
    external_id = models.PositiveIntegerField()
    model = models.CharField(max_length=80, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    price_rrc = models.PositiveIntegerField()  # рекомендованная розничная цена

    class Meta:
        verbose_name = 'Информация о товаре'
        unique_together = ('product', 'shop', 'external_id')

    def __str__(self):
        return f'{self.product.name} - {self.shop.name}'


class Parameter(models.Model):
    """Параметр товара (например: цвет, размер)"""
    name = models.CharField(max_length=40)

    class Meta:
        verbose_name = 'Параметр'

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """Значение параметра для конкретного товара"""
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name='product_parameters')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Параметр товара'
        unique_together = ('product_info', 'parameter')


class Contact(models.Model):
    """Адрес доставки покупателя"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    city = models.CharField(max_length=50)
    street = models.CharField(max_length=100)
    house = models.CharField(max_length=15, blank=True)
    apartment = models.CharField(max_length=15, blank=True)
    phone = models.CharField(max_length=20)

    class Meta:
        verbose_name = 'Контакт'

    def __str__(self):
        return f'{self.city}, {self.street}, {self.house}'


class Order(models.Model):
    """Заказ"""
    STATUS_CHOICES = (
        ('basket', 'В корзине'),
        ('new', 'Новый'),
        ('confirmed', 'Подтверждён'),
        ('assembled', 'Собран'),
        ('sent', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    dt = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'Заказ {self.id} от {self.user.email}'


class OrderItem(models.Model):
    """Позиция в заказе"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='ordered_items')
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Позиция заказа'
        unique_together = ('order', 'product_info')