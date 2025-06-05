import requests
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group, Permission, User
from django.urls import path
from bot.admin import CustomAdminSite, BaseCategoryAdmin, BaseQuestionAdmin, BaseFormQuestionAdmin, \
    BaseQuestionTopicNotificationAdmin
from bot.models import Category, Question, FormQuestion, QuestionTopicNotification
from chatterbot_model.admin import TagAdmin, TrainingPairAdmin
from chatterbot_model.models import TrainingPair, Tag


class CheckCreateAdminPage:
    """
    Проверяет и создаёт кастомные админ страницы на основе модели page
    """
    pages = []
    extra_admin_site_patterns = []

    def __init__(self):
        from bot.models import Page
        self.pages = Page.objects.all()

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
            list_model = [Question, Category, FormQuestion, QuestionTopicNotification, TrainingPair, Tag]
            admin_group = Group.objects.create(name=f'admin_page_{page.slug}')
            content_type = ContentType.objects.get_for_model(User)
            perm_staff = Permission.objects.create(name=f'Can login admin page {page.name}',
                                                   codename=f'admin_for_page_{page.id}',
                                                   content_type=content_type)
            admin_group.permissions.add(perm_staff)
            # добавление сторонних разрешений для существующих моделей
            for model in list_model:
                content_type = ContentType.objects.get_for_model(model)
                permissions = Permission.objects.filter(content_type=content_type)
                for perm in permissions:
                    admin_group.permissions.add(perm)
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

        class QuestionTopicNotificationAdmin(BaseQuestionTopicNotificationAdmin):
            model_admin_site = custom_admin

        # Регистрируем модели в текущем AdminSite
        custom_admin.register(Category, CategoryAdmin)
        custom_admin.register(Question, QuestionAdmin)
        custom_admin.register(FormQuestion, FormQuestionAdmin)
        custom_admin.register(QuestionTopicNotification, QuestionTopicNotificationAdmin)
        # Не имеет привязанности к определенной странице
        custom_admin.register(Tag, TagAdmin)
        custom_admin.register(TrainingPair, TrainingPairAdmin)

        return custom_admin

    def main(self) -> list:
        print('Проверка необходимых группы и разрешений')
        try:
            for page in self.pages:
                self.__check_or_create_group_permission(page)

                response = requests.get(str(page.url))
                if response.status_code == 200:
                    print(f'\033[32m Страница по адресу: {page.url} — активна \033[0m')
                else:
                    print(f'\033[31m Страница по адресу: {page.url} — !не отвечает! \033[0m')

                admin_site = self.__create_custom_admin_site(page)
                self.extra_admin_site_patterns.append(path(f'{page.slug}/', admin_site.urls))
        except:
            print(f'\033[31m Миграция модели Page не произведена! \033[0m')
        print('Проверка завершена')
        return self.extra_admin_site_patterns
