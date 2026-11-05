import json
from pathlib import Path
import requests


BASE_DIR = Path(__file__).resolve().parent

LOGIN_URL = "http://127.0.0.1:8000/api/v1/user/login"
IMPORT_URL = "http://127.0.0.1:8000/api/v1/partner/update"

YAML_FILE_PATH = BASE_DIR / "data" / "shop1.yaml"

LOGIN_DATA = {
    "email": "supplier@example.com",
    "password": "supplier123",
}


def print_response(response):
    """
    Аккуратно выводим ответ сервера.
    Если сервер вернул JSON — печатаем JSON.
    Если сервер вернул HTML с ошибкой — печатаем текст.
    """
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except ValueError:
        print(response.text)
        return None


print("=" * 60)
print("1. Проверяем наличие YAML-файла")
print("=" * 60)

print(f"Путь к файлу: {YAML_FILE_PATH}")

if not YAML_FILE_PATH.exists():
    print("Файл shop1.yaml не найден!")
    print("Проверьте, что он лежит в папке data в корне проекта.")
    raise SystemExit(1)

print("Файл найден")
print()


print("=" * 60)
print("2. Авторизуемся как поставщик")
print("=" * 60)

response = requests.post(LOGIN_URL, json=LOGIN_DATA)

print(f"HTTP статус: {response.status_code}")
login_result = print_response(response)

if not login_result or not login_result.get("Status"):
    print("Не удалось войти.")
    print("Проверьте, создан ли пользователь supplier@example.com и пароль supplier123.")
    raise SystemExit(1)

token = login_result["Token"]
headers = {
    "Authorization": f"Token {token}",
}

print()
print("Авторизация успешна")
print(f"Токен: {token[:20]}...")
print()


print("=" * 60)
print("3. Запускаем импорт товаров")
print("=" * 60)

import_data = {
    "url": str(YAML_FILE_PATH),
}

response_import = requests.post(
    IMPORT_URL,
    json=import_data,
    headers=headers,
)

print(f"HTTP статус: {response_import.status_code}")
import_result = print_response(response_import)

if response_import.status_code == 200 and import_result and import_result.get("Status"):
    print()
    print("Импорт успешно завершён")
else:
    print()
    print("Импорт завершился с ошибкой")