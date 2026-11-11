from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.db.models import Sum, F

from backend.models import (
    User, Shop, Category, Product, ProductInfo, 
    Parameter, ProductParameter, Order, OrderItem, 
    Contact, ConfirmEmailToken
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Панель управления пользователями"""
    model = User
    
    list_display = ('email', 'first_name', 'last_name', 'type', 'is_active', 'is_staff')
    list_filter = ('type', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'company')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Права доступа', {
            'fields': ('type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'type', 'is_active', 'is_staff'),
        }),
    )


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Управление магазинами"""
    list_display = ('name', 'user', 'state', 'categories_count', 'products_count')
    list_filter = ('state',)
    search_fields = ('name', 'user__email')
    
    def categories_count(self, obj):
        return obj.categories.count()
    categories_count.short_description = 'Категорий'
    
    def products_count(self, obj):
        return obj.product_infos.count()
    products_count.short_description = 'Товаров'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Управление категориями"""
    list_display = ('name', 'shops_count', 'products_count')
    search_fields = ('name',)
    
    def shops_count(self, obj):
        return obj.shops.count()
    shops_count.short_description = 'Магазинов'
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Товаров'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Управление товарами"""
    list_display = ('name', 'category', 'shops_count')
    list_filter = ('category',)
    search_fields = ('name',)
    
    def shops_count(self, obj):
        return obj.product_infos.count()
    shops_count.short_description = 'Магазинов'


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """Управление информацией о товарах в магазинах"""
    list_display = ('product', 'shop', 'price', 'price_rrc', 'quantity', 'external_id')
    list_filter = ('shop', 'product__category')
    search_fields = ('product__name', 'shop__name', 'model')
    raw_id_fields = ('product', 'shop')


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """Управление параметрами товаров"""
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """Управление значениями параметров товаров"""
    list_display = ('product_info', 'parameter', 'value')
    list_filter = ('parameter',)
    search_fields = ('product_info__product__name', 'parameter__name', 'value')
    raw_id_fields = ('product_info', 'parameter')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Управление контактами пользователей"""
    list_display = ('user', 'city', 'street', 'house', 'apartment', 'phone')
    list_filter = ('city',)
    search_fields = ('user__email', 'city', 'street', 'phone')
    raw_id_fields = ('user',)


class OrderItemInline(admin.TabularInline):
    """Inline для отображения позиций заказа прямо в форме заказа"""
    model = OrderItem
    extra = 0
    readonly_fields = ('product_info', 'quantity')
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Управление заказами - САМАЯ ВАЖНАЯ ЧАСТЬ АДМИНКИ"""
    list_display = ('id', 'user', 'dt', 'state', 'contact_display', 'total_sum_display', 'items_count')
    list_filter = ('state', 'dt')
    search_fields = ('user__email', 'id')
    date_hierarchy = 'dt'
    raw_id_fields = ('user', 'contact')
    readonly_fields = ('dt', 'total_sum_display', 'items_display')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'dt', 'state', 'contact')
        }),
        ('Детали заказа', {
            'fields': ('total_sum_display', 'items_display'),
            'classes': ('collapse',)
        }),
    )
    
    def contact_display(self, obj):
        if obj.contact:
            return f"{obj.contact.city}, {obj.contact.street}, {obj.contact.house}"
        return '-'
    contact_display.short_description = 'Адрес доставки'
    
    def total_sum_display(self, obj):
        total = obj.ordered_items.aggregate(
            total=Sum(F('quantity') * F('product_info__price'))
        )['total']
        return f"{total or 0} руб."
    total_sum_display.short_description = 'Сумма заказа'
    
    def items_count(self, obj):
        return obj.ordered_items.count()
    items_count.short_description = 'Позиций'
    
    def items_display(self, obj):
        items = obj.ordered_items.select_related('product_info__product', 'product_info__shop')
        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr style="background:#f0f0f0;"><th style="padding:8px; border:1px solid #ddd;">Товар</th>'
        html += '<th style="padding:8px; border:1px solid #ddd;">Магазин</th>'
        html += '<th style="padding:8px; border:1px solid #ddd;">Кол-во</th>'
        html += '<th style="padding:8px; border:1px solid #ddd;">Цена</th>'
        html += '<th style="padding:8px; border:1px solid #ddd;">Сумма</th></tr>'
        
        for item in items:
            subtotal = item.quantity * item.product_info.price
            html += f'<tr>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{item.product_info.product.name}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{item.product_info.shop.name}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{item.quantity}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{item.product_info.price} руб.</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{subtotal} руб.</td>'
            html += f'</tr>'
        
        html += '</table>'
        return format_html(html)
    items_display.short_description = 'Состав заказа'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Управление позициями заказа"""
    list_display = ('order', 'product_info', 'quantity', 'price_display')
    list_filter = ('order__state',)
    search_fields = ('order__id', 'product_info__product__name')
    raw_id_fields = ('order', 'product_info')
    
    def price_display(self, obj):
        return f"{obj.product_info.price} руб."
    price_display.short_description = 'Цена'


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """Управление токенами подтверждения email"""
    list_display = ('user', 'key', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'key')
    readonly_fields = ('key', 'created_at')
    raw_id_fields = ('user',)