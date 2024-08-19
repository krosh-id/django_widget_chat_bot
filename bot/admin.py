from django.contrib import admin
from django.http import Http404
from rest_framework.response import Response

from .models import Page, Category, Question, FormQuestion

# Главная админка
admin.site.register(Page)
admin.site.register(Category)
admin.site.register(Question)


# Дополнительные кастомные админки
class CustomAdminSite(admin.AdminSite):
    def __init__(self, page_id, page_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_name = page_name
        self.page_id = page_id
        self.site_header = f'Панель администрирования виджета страницы {page_name}'
        self.site_title = f'Страница Администратора виджета {page_name}'
        self.index_title = f'Стартовая страница Администратора виджета {page_name}'


# Базовые админ-классы для Category, Question и FormQuestion
class BaseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'page', 'created_by')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(page=self.model_admin_site.page_id)


class BaseQuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'category', 'is_published', 'created_by')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(category__page=self.model_admin_site.page_id)


class BaseFormQuestionAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'date_created', 'page')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(page=self.model_admin_site.page_id)


# Фабричная функция для создания AdminSite и регистрации моделей
def create_custom_admin_site(page_id: int, page_name: str) -> CustomAdminSite:
    custom_admin = CustomAdminSite(name=f'admin_page_{page_name}',
                                   page_id=page_id,
                                   page_name=page_name,
                                   )

    # Определяем админ-классы, связывая их с текущим AdminSite
    class CategoryAdmin(BaseCategoryAdmin):
        model_admin_site = custom_admin

    class QuestionAdmin(BaseQuestionAdmin):
        model_admin_site = custom_admin

    class FormQuestionAdmin(BaseFormQuestionAdmin):
        model_admin_site = custom_admin

    # Регистрируем модели в текущем AdminSite
    custom_admin.register(Category, CategoryAdmin)
    custom_admin.register(Question, QuestionAdmin)
    custom_admin.register(FormQuestion, FormQuestionAdmin)

    return custom_admin

