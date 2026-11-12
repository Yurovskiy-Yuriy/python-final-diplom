from django.core.management.base import BaseCommand
from django.conf import settings
from yaml import load as load_yaml, Loader

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter


class Command(BaseCommand):
    help = 'Загружает демонстрационные данные: создаёт тестового поставщика и импортирует товары из shop1.yaml'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Начинаю загрузку данных...'))
        
        # 1. Создаём тестового поставщика
        self.stdout.write('Создаю тестового поставщика...')
        supplier, created = User.objects.get_or_create(
            email='supplier@example.com',
            defaults={
                'first_name': 'Поставщик',
                'last_name': 'Тестовый',
                'type': 'shop',
                'is_active': True,
            }
        )
        if created:
            supplier.set_password('supplier123')
            supplier.save()
            self.stdout.write(self.style.SUCCESS(f'Поставщик создан: {supplier.email} / supplier123'))
        else:
            self.stdout.write(self.style.WARNING(f'Поставщик уже существует: {supplier.email}'))
        
        # 2. Создаём тестового покупателя
        self.stdout.write('👤 Создаю тестового покупателя...')
        buyer, created = User.objects.get_or_create(
            email='buyer@example.com',
            defaults={
                'first_name': 'Покупатель',
                'last_name': 'Тестовый',
                'type': 'buyer',
                'is_active': True,
            }
        )
        if created:
            buyer.set_password('buyer123')
            buyer.save()
            self.stdout.write(self.style.SUCCESS(f'Покупатель создан: {buyer.email} / buyer123'))
        else:
            self.stdout.write(self.style.WARNING(f'Покупатель уже существует: {buyer.email}'))
        
        # 3. Импортируем товары из shop1.yaml
        self.stdout.write('Импортирую товары из shop1.yaml...')
        yaml_path = settings.BASE_DIR / 'data' / 'shop1.yaml'
        
        if not yaml_path.exists():
            self.stdout.write(self.style.ERROR(f'Файл не найден: {yaml_path}'))
            return
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = load_yaml(f, Loader=Loader)
        
        # Создаём магазин
        shop, _ = Shop.objects.get_or_create(
            name=data['shop'],
            defaults={'user_id': supplier.id, 'state': True}
        )
        self.stdout.write(f'Магазин: {shop.name}')
        
        # Создаём категории
        categories_created = 0
        for category in data.get('categories', []):
            category_object, created = Category.objects.get_or_create(
                id=category['id'],
                defaults={'name': category['name']}
            )
            category_object.shops.add(shop.id)
            if created:
                categories_created += 1
        
        self.stdout.write(f'Создано категорий: {categories_created}')
        
        # Создаём товары
        products_created = 0
        products_updated = 0
        for item in data.get('goods', []):
            product, _ = Product.objects.get_or_create(
                name=item['name'],
                defaults={'category_id': item['category']}
            )
            
            product_info, created = ProductInfo.objects.get_or_create(
                product_id=product.id,
                external_id=item['id'],
                defaults={
                    'model': item.get('model', ''),
                    'price': item['price'],
                    'price_rrc': item.get('price_rrc', 0),
                    'quantity': item['quantity'],
                    'shop_id': shop.id,
                }
            )
            
            if created:
                products_created += 1
            else:
                # Обновляем существующий товар
                product_info.price = item['price']
                product_info.price_rrc = item.get('price_rrc', 0)
                product_info.quantity = item['quantity']
                product_info.save()
                products_updated += 1
            
            # Параметры
            ProductParameter.objects.filter(product_info_id=product_info.id).delete()
            parameters = item.get('parameters', {})
            if isinstance(parameters, dict):
                for param_name, param_value in parameters.items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=param_name)
                    ProductParameter.objects.create(
                        product_info_id=product_info.id,
                        parameter_id=parameter_object.id,
                        value=str(param_value)
                    )
        
        self.stdout.write(self.style.SUCCESS(
            f'Товаров создано: {products_created}, обновлено: {products_updated}'
        ))
        
        # Итоговая статистика
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Демонстрационные данные успешно загружены!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Статистика:'))
        self.stdout.write(f'   • Пользователей: {User.objects.count()}')
        self.stdout.write(f'   • Магазинов: {Shop.objects.count()}')
        self.stdout.write(f'   • Категорий: {Category.objects.count()}')
        self.stdout.write(f'   • Товаров: {Product.objects.count()}')
        self.stdout.write(f'   • Позиций в магазинах: {ProductInfo.objects.count()}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Данные для входа:'))
        self.stdout.write(f'   Поставщик: {supplier.email} / supplier123')
        self.stdout.write(f'   Покупатель: {buyer.email} / buyer123')