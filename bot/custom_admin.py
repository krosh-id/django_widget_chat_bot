import requests
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group, Permission, User
from django.urls import path
from bot.admin import CustomAdminSite, BaseCategoryAdmin, BaseQuestionAdmin, BaseFormQuestionAdmin
from bot.models import Category, Question, FormQuestion


class CheckCreateAdminPage:
    """
    Проверяет и создаёт кастомные админ страницы на основе модели page
    """
    pages = []
    extra_admin_site_patterns = []

    def __init__(self):
        from bot.models import Page
        pages = Page.objects.all()
        print('Миграция модели Page не произведена!')
        self.pages = pages

    @staticmethod
    def __check_or_create_group_permission(page):
        """
        Создает, если не существует, группы пользователей и разрешения для доступа к админ панелям.
        :param page:
        :return:
        """
        print('Проверка необходимых группы и разрешений')
        groups_name = Group.objects.all().values_list('name', flat=True)
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
    @staticmethod
    def __create_custom_admin_site(page) -> CustomAdminSite:
        """
        Фабричная функция для создания кастомных AdminSite и регистрации моделей
        :param page:
        :return:
        """
        custom_admin = CustomAdminSite(name=f'admin_page_{page.name}',
                                       page_id=page.id,
                                       page_name=page.name,
                                       site_url=page.url
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

    def main(self) -> list:
        print('Проверка необходимых группы и разрешений')
        for page in self.pages:
            self.__check_or_create_group_permission(page)

            response = requests.get(str(page.url))
            if response.status_code == 200:
                print(f'\033[32m Страница по адресу: {page.url} — активна \033[0m')
            else:
                print(f'\033[31m Страница по адресу: {page.url} — !не отвечает! \033[0m')

            admin_site = self.__create_custom_admin_site(page)
            self.extra_admin_site_patterns.append(path(f'{page.slug}/', admin_site.urls))

        print('Проверка завершена')
        return self.extra_admin_site_patterns
