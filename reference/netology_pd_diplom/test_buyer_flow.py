"""
Этот скрипт предназначен для демонстрации работы API через реальные HTTP-запросы.
Для автоматического тестирования используйте команду: python3 manage.py test backend
"""
import json
import requests


BASE_URL = "http://127.0.0.1:8000/api/v1"

LOGIN_URL = f"{BASE_URL}/user/login"
PRODUCTS_URL = f"{BASE_URL}/products"
BASKET_URL = f"{BASE_URL}/basket"
CONTACT_URL = f"{BASE_URL}/user/contact"
ORDER_URL = f"{BASE_URL}/order"

BUYER_CREDENTIALS = {
    "email": "buyer@example.com",
    "password": "buyer123"
}


def print_response(response, title=""):
    """Аккуратно выводим ответ сервера"""
    if title:
        print(f"\n{title}")
    print(f"HTTP статус: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except ValueError:
        print(response.text)
        return None


print("=" * 70)
print("ТЕСТИРОВАНИЕ ПОЛНОГО СЦЕНАРИЯ ПОКУПКИ")
print("=" * 70)


# 1. Авторизация покупателя
print("\n1. Авторизуемся как покупатель...")
response = requests.post(LOGIN_URL, json=BUYER_CREDENTIALS)
login_result = print_response(response)

if not login_result or not login_result.get("Status"):
    print("Не удалось войти")
    raise SystemExit(1)

token = login_result["Token"]
headers = {"Authorization": f"Token {token}"}
print("Авторизация успешна")


# 2. Получаем список товаров
print("\n2. Получаем список товаров...")
response = requests.get(PRODUCTS_URL, headers=headers)
products_result = print_response(response)

if not products_result:
    print("Не удалось получить товары")
    raise SystemExit(1)

# Выбираем первый товар для добавления в корзину
if len(products_result) > 0:
    first_product = products_result[0]
    product_info_id = first_product['id']
    print(f"Получено товаров: {len(products_result)}")
    print(f"Выбран товар: {first_product['product']['name']} (ID: {product_info_id})")
else:
    print("Нет товаров в базе")
    raise SystemExit(1)


# 3. Добавляем товар в корзину
print("\n3. Добавляем товар в корзину...")
basket_items = json.dumps([
    {
        "product_info": product_info_id,
        "quantity": 2
    }
])
response = requests.post(
    BASKET_URL,
    json={"items": basket_items},
    headers=headers
)
basket_result = print_response(response)

if not basket_result or not basket_result.get("Status"):
    print("Не удалось добавить товар в корзину")
    raise SystemExit(1)

print("Товар добавлен в корзину")


# 4. Просматриваем корзину
print("\n4. Просматриваем корзину...")
response = requests.get(BASKET_URL, headers=headers)
basket_view = print_response(response)

if basket_view and len(basket_view) > 0:
    basket_id = basket_view[0]['id']
    total_sum = basket_view[0].get('total_sum', 0)
    print(f"Корзина: ID={basket_id}, Сумма={total_sum} руб.")
else:
    print("Корзина пуста")
    raise SystemExit(1)


# 5. Создаем контакт (адрес доставки)
print("\n5. Создаем контакт (адрес доставки)...")
contact_data = {
    "city": "Москва",
    "street": "ул. Ленина",
    "house": "10",
    "apartment": "25",
    "phone": "+79991234567"
}
response = requests.post(CONTACT_URL, json=contact_data, headers=headers)
contact_result = print_response(response)

if not contact_result or not contact_result.get("Status"):
    print("Не удалось создать контакт")
    raise SystemExit(1)

print("Контакт создан")


# 6. Получаем список контактов
print("\n6. Получаем список контактов...")
response = requests.get(CONTACT_URL, headers=headers)
contacts_list = print_response(response)

if contacts_list and len(contacts_list) > 0:
    contact_id = contacts_list[0]['id']
    print(f"Получено контактов: {len(contacts_list)}, ID первого: {contact_id}")
else:
    print("Нет контактов")
    raise SystemExit(1)


# 7. Подтверждаем заказ
print("\n7. Подтверждаем заказ...")
order_data = {
    "id": basket_id,
    "contact": contact_id
}
response = requests.post(ORDER_URL, json=order_data, headers=headers)
order_result = print_response(response)

if not order_result or not order_result.get("Status"):
    print("Не удалось подтвердить заказ")
    raise SystemExit(1)

print("Заказ подтвержден")


# 8. Получаем список заказов
print("\n8. Получаем список заказов...")
response = requests.get(ORDER_URL, headers=headers)
orders_list = print_response(response)

if orders_list and len(orders_list) > 0:
    print(f"Получено заказов: {len(orders_list)}")
    for order in orders_list:
        print(f"   - Заказ #{order['id']}, Статус: {order['state']}, Сумма: {order.get('total_sum', 0)} руб.")
else:
    print("Нет заказов")


print("\n" + "=" * 70)
print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
print("=" * 70)