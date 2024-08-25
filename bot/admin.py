from django.contrib import admin
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
from .models import Page, Category, Question, FormQuestion

# Главная админка
admin.site.register(Page)
admin.site.register(Category)
admin.site.register(Question)


# Дополнительные кастомные админки
class CustomAdminSite(admin.AdminSite):
    def __init__(self, page_id, page_name, site_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_name = page_name
        self.page_id = page_id
        self.site_header = f'Панель администрирования виджета страницы {page_name}'
        self.site_title = f'Страница Администратора виджета {page_name}'
        self.index_title = f'Управление виджетом {page_name}'
        self.site_url = site_url

    def get_urls(self):
        from django.urls import path
        urls = super(CustomAdminSite, self).get_urls()
        urls = [
                   path('site_url/', lambda request: redirect(self.site_url), name='site_url'),
               ] + urls
        return urls

    def has_permission(self, request):
        if request.user.is_superuser:
            return True
        if request.user.is_staff:
            return request.user.has_perm(f'auth.admin_for_page_{self.page_id}')
        return False


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


# Создает, если не существует, группы пользователей и разрешения для доступа к админ панелям
# Фабричная функция для создания AdminSite и регистрации моделей

