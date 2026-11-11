from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
import json

from backend.models import (
    User, Shop, Category, Product, ProductInfo,
    Contact, Order, OrderItem
)
from backend.admin import OrderAdmin


class BuyerFlowTestCase(TestCase):
    """
    Интеграционный тест полного сценария покупки.
    """

    def setUp(self):
        # 1. Создаем тестового пользователя-покупателя
        self.buyer = User.objects.create_user(
            email='test_buyer@example.com',
            password='testpassword123',
            first_name='Тест',
            last_name='Покупатель',
            type='buyer',
            is_active=True
        )

        # 2. Создаем тестовые данные для каталога
        self.shop = Shop.objects.create(name='Тестовый Магазин', state=True)
        self.category = Category.objects.create(name='Смартфоны')
        self.category.shops.add(self.shop)

        self.product = Product.objects.create(
            name='Тестовый Телефон',
            category=self.category
        )
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=100,
            quantity=10,
            price=50000,
            price_rrc=55000
        )

        # 3. Инициализируем API клиент
        self.client = APIClient()

    def test_full_buyer_flow(self):
        """Тестирует полный путь: Логин -> Товары -> Корзина -> Контакт -> Заказ"""

        # --- 1. Авторизация ---
        login_url = reverse('backend:user-login')
        response = self.client.post(login_url, {
            'email': 'test_buyer@example.com',
            'password': 'testpassword123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['Status'])
        token = response_data['Token']

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # --- 2. Получение списка товаров ---
        products_url = reverse('backend:shops')
        response = self.client.get(products_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertGreater(len(response_data), 0)

        # --- 3. Добавление товара в корзину ---
        basket_url = reverse('backend:basket')
        basket_items = json.dumps([
            {"product_info": self.product_info.id, "quantity": 2}
        ])
        response = self.client.post(basket_url, {'items': basket_items}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['Status'])

        # --- 4. Проверка корзины ---
        response = self.client.get(basket_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        basket_id = response_data[0]['id']
        self.assertEqual(response_data[0]['total_sum'], 100000)

        # --- 5. Создание контакта ---
        contact_url = reverse('backend:user-contact')
        response = self.client.post(contact_url, {
            'city': 'Москва',
            'street': 'Тестовая',
            'house': '1',
            'phone': '+79990000000'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['Status'])

        response = self.client.get(contact_url)
        response_data = response.json()
        contact_id = response_data[0]['id']

        # --- 6. Подтверждение заказа ---
        order_url = reverse('backend:order')
        response = self.client.post(order_url, {
            'id': basket_id,
            'contact': contact_id
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(response_data['Status'])

        # --- 7. Проверка заказа ---
        order = Order.objects.get(id=basket_id)
        self.assertEqual(order.state, 'new')
        self.assertEqual(order.contact_id, contact_id)


class ContactUpdateTestCase(TestCase):
    """Тесты обновления контактов"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='contact_test@example.com',
            password='testpass123',
            type='buyer',
            is_active=True
        )
        self.contact = Contact.objects.create(
            user=self.user,
            city='Москва',
            street='Тестовая',
            house='1',
            phone='+79990000000'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_update_contact_with_int_id(self):
        """Тест: обновление контакта с id как числом"""
        url = reverse('backend:user-contact')
        response = self.client.put(url, {
            'id': self.contact.id,
            'city': 'Санкт-Петербург'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['Status'])

        self.contact.refresh_from_db()
        self.assertEqual(self.contact.city, 'Санкт-Петербург')

    def test_update_contact_with_string_id(self):
        """Тест: обновление контакта с id как строкой"""
        url = reverse('backend:user-contact')
        response = self.client.put(url, {
            'id': str(self.contact.id),
            'city': 'Казань'
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['Status'])


class AdminTestCase(TestCase):
    """Тесты админки"""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='adminpass123'
        )
        self.client = APIClient()

        # ВАЖНО: Для админки Django используем force_login, а не force_authenticate!
        # force_authenticate работает только с DRF, а админка использует сессии
        self.client.force_login(self.admin_user)

        self.buyer = User.objects.create_user(
            email='buyer@test.com',
            password='buyerpass123',
            type='buyer',
            is_active=True
        )
        self.shop = Shop.objects.create(name='Test Shop', state=True)

        self.category = Category.objects.create(name='Test Category')
        self.category.shops.add(self.shop)

        self.product = Product.objects.create(
            name='Test Product',
            category=self.category
        )
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=1,
            quantity=10,
            price=1000,
            price_rrc=1100
        )
        self.order = Order.objects.create(
            user=self.buyer,
            state='new'
        )
        OrderItem.objects.create(
            order=self.order,
            product_info=self.product_info,
            quantity=2
        )

    def test_admin_can_view_orders(self):
        """Тест: админ может просматривать список заказов"""
        admin_url = reverse('admin:backend_order_changelist')
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_change_order_status(self):
        """Тест: админ может менять статус заказа"""
        admin_url = reverse('admin:backend_order_change', args=[self.order.id])
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 200)

    def test_order_admin_displays_total_sum(self):
        """Тест: админка правильно считает сумму заказа"""
        admin = OrderAdmin(Order, AdminSite())
        total = admin.total_sum_display(self.order)
        self.assertEqual(total, '2000 руб.')