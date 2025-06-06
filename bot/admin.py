from django.contrib import admin
from django.shortcuts import redirect
from chatterbot_model.models_chat import LibraryBotModel
from .models import Page, Category, Question, FormQuestion, QuestionTopicNotification


class CategoryAdmin(admin.ModelAdmin):
    exclude = ('created_by',)
    list_display = ('name', 'created_by', 'page')

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:  # Если поле author еще не заполнено
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


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

    def site_redirect_view(self, request):
        return redirect(self.site_url)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        urls = [path('site_url/', self.site_redirect_view, name='site_url')] + urls
        return urls

    def has_permission(self, request):
        if request.user.is_superuser:
            return True
        if request.user.is_staff:
            return request.user.has_perm(f'auth.admin_for_page_{self.page_id}')
        return False


# Базовые админ-классы для Category, Question и FormQuestion
class BaseCategoryAdmin(admin.ModelAdmin):
    model_admin_site = None  # CustomAdminSite()
    list_display = ('name', 'created_by')
    exclude = ('created_by', 'page')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.model_admin_site:
            return qs.filter(page=self.model_admin_site.page_id)
        return qs

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:  # Если поле author еще не заполнено
            obj.created_by = request.user
            obj.page_id = self.model_admin_site.page_id
        super().save_model(request, obj, form, change)

# Выбор тегов для вопросов на основе tag_id
# class QuestionAdminForm(forms.ModelForm):
#     tag = forms.ModelChoiceField(
#         queryset=Tag.objects.using('chatbot').all(),
#         required=False,
#         label='Тег',
#         initial=None
#     )
#
#     class Meta:
#         model = Question
#         fields = [f.name for f in Question._meta.fields if f.editable and f.name != 'tag_id'] + ['tag']
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Установить текущее значение по id
#         if self.instance and self.instance.tag_id:
#             try:
#                 self.fields['tag'].initial = Tag.objects.using('chatbot').get(id=self.instance.tag_id)
#             except Tag.DoesNotExist:
#                 pass
#
#     def save(self, commit=True):
#         # Сохранить выбранный тег в tag_id
#         instance = super().save(commit=False)
#         tag = self.cleaned_data.get('tag')
#         instance.tag_id = tag.id if tag else None
#         if commit:
#             instance.save()
#         return instance

class BaseQuestionAdmin(admin.ModelAdmin):
    # form = QuestionAdminForm
    model_admin_site = None # CustomAdminSite()
    list_display = ('text', 'category', 'is_published', 'order')
    list_editable = ('order',)
    exclude = ('created_by', )
    actions = ['reset_model']

    # def tag_name(self, obj):
    #     try:
    #         tag = Tag.objects.using('chatbot').get(id=obj.tag_id)
    #         return tag.name
    #     except Tag.DoesNotExist:
    #         return 'Неизвестный тег'
    # tag_name.short_description = 'Тег'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.model_admin_site:
            return qs.filter(category__page=self.model_admin_site.page_id)
        return qs

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:  # Если поле author еще не заполнено
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def reset_model(self, request, queryset):
        """
        Сбрасывает данные обучения бота, создаёт JSON файл и обучается.
        """
        bot = LibraryBotModel.get_instance()
        try:
            bot.reset_model()
            self.message_user(request, "Модель успешно сброшена и переобучена из JSON")
        except Exception as e:
            self.message_user(request, f"Ошибка при сбросе и переобучении модели: {e}", level='error')

    reset_model.short_description = "Обучить"


class BaseFormQuestionAdmin(admin.ModelAdmin):
    model_admin_site = None  # CustomAdminSite()
    list_display = ('full_name', 'email', 'date_created', 'page')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.model_admin_site:
            return qs.filter(page=self.model_admin_site.page_id)
        return qs


class BaseQuestionTopicNotificationAdmin(admin.ModelAdmin):
    model_admin_site = None  # CustomAdminSite()
    list_display = ('topic', 'send_to_email', 'page')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.model_admin_site:
            return qs.filter(page=self.model_admin_site.page_id)
        return qs

# Создает, если не существует, группы пользователей и разрешения для доступа к админ панелям
# Фабричная функция для создания AdminSite и регистрации моделей

admin.site.register(Page)
admin.site.register(Category)
admin.site.register(Question, BaseQuestionAdmin)
admin.site.register(FormQuestion, BaseFormQuestionAdmin)  # Используем BaseFormQuestionAdmin
admin.site.register(QuestionTopicNotification, BaseQuestionTopicNotificationAdmin)