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
def check_or_create_group_permission(pages: list):
    print('Проверка необходимых группы и разрешений')
    groups_name = Group.objects.all().values_list('name', flat=True)

    for page in pages:
        if not f'admin_page_{page.slug}' in groups_name:
            admin_group = Group.objects.create(name=f'admin_page_{page.slug}')
            content_type = ContentType.objects.get_for_model(User)
            perm_staff = Permission.objects.create(name=f'Can login admin page {page.name}',
                                                   codename=f'admin_for_page_{page.id}',
                                                   content_type=content_type)
            admin_group.permissions.add(perm_staff)
            print(f'Группа пользователей admin_page_{page.slug} с разрешением '
                  f'на вход admin_for_page_{page.id} была создана')
    print('Проверка завершена')


# Фабричная функция для создания AdminSite и регистрации моделей
def create_custom_admin_site(page_id: int, page_name: str, site_url: str) -> CustomAdminSite:
    custom_admin = CustomAdminSite(name=f'admin_page_{page_name}',
                                   page_id=page_id,
                                   page_name=page_name,
                                   site_url=site_url
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

