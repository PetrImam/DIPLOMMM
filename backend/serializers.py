from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User, Shop, Category, Product, ProductInfo, ProductParameter, Contact, Order, OrderItem


class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор регистрации пользователя.
    Пароль прогоняется через стандартные Django-валидаторы
    (AUTH_PASSWORD_VALIDATORS из settings.py): минимальная длина,
    проверка на схожесть с другими полями, "распространённость" пароля и т.д.
    create_user() сам по себе эти проверки не выполняет, поэтому валидация
    обязательно делается здесь, на уровне сериализатора.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'first_name', 'last_name',
                  'company', 'position', 'user_type']

    def validate_password(self, value):
        # validate_password принимает опционально экземпляр пользователя,
        # чтобы UserAttributeSimilarityValidator мог сравнить пароль
        # с email/именем — на момент регистрации полноценного instance ещё
        # нет, поэтому собираем временный (несохранённый) объект из initial_data.
        temp_user = User(
            email=self.initial_data.get('email', ''),
            username=self.initial_data.get('username', ''),
            first_name=self.initial_data.get('first_name', ''),
            last_name=self.initial_data.get('last_name', ''),
        )
        try:
            validate_password(value, user=temp_user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'city', 'street', 'house', 'apartment', 'phone']


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'company', 'position', 'user_type', 'contacts']


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'url', 'state']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'category']


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    shop = ShopSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(many=True, read_only=True)

    class Meta:
        model = ProductInfo
        fields = ['id', 'product', 'shop', 'model', 'quantity', 'price', 'price_rrc', 'product_parameters']


class OrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'dt', 'status', 'contact', 'ordered_items', 'total_sum']

    def get_total_sum(self, obj):
        return sum(item.quantity * item.product_info.price for item in obj.ordered_items.all())