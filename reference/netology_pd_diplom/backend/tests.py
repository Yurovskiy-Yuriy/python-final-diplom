from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
import json

from backend.models import User, Shop, Category, Product, ProductInfo, Contact, Order


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
        
        self.product = Product.objects.create(name='Тестовый Телефон', category=self.category)
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
        response_data = response.json()  # Используем .json() вместо .data
        self.assertTrue(response_data['Status'])
        token = response_data['Token']
        
        # Устанавливаем токен для всех последующих запросов
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
        self.assertEqual(response_data[0]['total_sum'], 100000)  # 2 * 50000

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

        # Получаем ID созданного контакта
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

        # --- 7. Проверка, что заказ создан и статус изменился ---
        order = Order.objects.get(id=basket_id)
        self.assertEqual(order.state, 'new')
        self.assertEqual(order.contact_id, contact_id)