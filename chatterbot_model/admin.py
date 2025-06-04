from django.contrib import admin
from .models import ChatLog, TrainingPair, Tag, Statement
from .models_chat import LibraryBotModel


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Meta:
        model = Tag

@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = ('text', 'in_response_to', 'conversation', 'created_at', 'persona')
    search_fields = ('text', 'in_response_to', 'conversation', 'persona')
    list_filter = ('created_at', 'conversation', 'persona')
    date_hierarchy = 'created_at'

    # Отключаем возможность добавления
    def has_add_permission(self, request):
        return False

    # Отключаем возможность изменения
    def has_change_permission(self, request, obj=None):
        return False

    class Meta:
        model = Statement


# добавить айди к таблице
# @admin.register(TagAssociation)
# class TagAssociationAdmin(admin.ModelAdmin):
#     list_display = ('statement_text', 'tag_name')
#     search_fields = ('statement__text', 'tag__name')
#     list_filter = ('tag__name',)
#
#     # Отображаем текст высказывания и имя тега
#     def statement_text(self, obj):
#         return obj.statement.text
#
#     statement_text.short_description = 'Высказывание'
#
#     def tag_name(self, obj):
#         return obj.tag.name
#
#     tag_name.short_description = 'Тег'
#
#     # Отключаем возможность добавления
#     def has_add_permission(self, request):
#         return False
#
#     # Отключаем возможность изменения
#     def has_change_permission(self, request, obj=None):
#         return False
#
#     # Отключаем возможность удаления
#     def has_delete_permission(self, request, obj=None):
#         return False
#
#     class Meta:
#         model = TagAssociation

@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('user_message', 'bot_response', 'created_at', 'is_training_pair')
    list_filter = ('created_at', 'is_training_pair')
    search_fields = ('user_message', 'bot_response')


@admin.register(TrainingPair)
class TrainingPairAdmin(admin.ModelAdmin):
    list_display = ('question', 'answer', 'created_at', 'is_applied')
    list_filter = ('is_applied', 'created_at')
    search_fields = ('question', 'answer')
    actions = ['train_bot', 'reset_model']

    def save_model(self, request, obj, form, change):
        if not obj.question or not obj.answer:
            self.message_user(request, "Вопрос и ответ не могут быть пустыми", level='error')
            return
        super().save_model(request, obj, form, change)

    def train_bot(self, request, queryset):
        """
        Действие для дообучения бота на выбранных парах.
        """
        bot = LibraryBotModel.get_instance()
        for pair in queryset.filter(is_applied=False):
            try:
                bot.train_from_pair(pair.question, pair.answer)
                pair.is_applied = True
                pair.save()
                self.message_user(request, f"Бот дообучен на паре: '{pair.question}' -> '{pair.answer}'")
            except Exception as e:
                self.message_user(request, f"Ошибка при обучении на паре '{pair.question}': {e}", level='error')

    train_bot.short_description = "Дообучить бота на выбранных парах"

    def reset_model(self, request, queryset):
        """
        Сбрасывает данные обучения бота и переобучает его из JSON.
        """
        bot = LibraryBotModel.get_instance()
        try:
            json_directory = "./chatterbot_model/data/training_data.json"
            bot.reset_model(json_directory)
            self.message_user(request, "Модель успешно сброшена и переобучена из JSON")
        except Exception as e:
            self.message_user(request, f"Ошибка при сбросе и переобучении модели: {e}", level='error')

    reset_model.short_description = "Переобучить модель из JSON"
