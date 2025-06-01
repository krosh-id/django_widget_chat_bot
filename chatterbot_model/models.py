from django.db import models

# дефолтные модели chatterbot
class Tag(models.Model):
    """
    Модель для хранения тегов, используемых для категоризации высказываний.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="Тег")

    class Meta:
        db_table = 'tag'
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name

# дефолтные модели chatterbot
class Statement(models.Model):
    """
    Модель для хранения высказываний (вопросов и ответов) чат-бота.
    """
    text = models.TextField(verbose_name="Высказывание")
    search_text = models.TextField(default="", null=False)
    conversation = models.CharField(max_length=32, default="", null=False, verbose_name="Тег")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    in_response_to = models.TextField(verbose_name="Ответ на: ", blank=True, null=True)
    search_in_response_to = models.TextField(default="", null=False)
    persona = models.CharField(max_length=32, default="", null=False, verbose_name="Персона")

    class Meta:
        db_table = 'statement'
        verbose_name = "Высказывание"
        verbose_name_plural = "Высказывания"

    def __str__(self):
        return self.text

class TagAssociation(models.Model):
    """
    Модель для связи многие-ко-многим между Statement и Tag.
    """
    statement = models.ForeignKey(Statement, on_delete=models.CASCADE, related_name='tag_associations')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='tag_associations')

    class Meta:
        db_table = 'tag_association'
        verbose_name = "Ассоциация тега"
        verbose_name_plural = "Ассоциации тегов"
        unique_together = ('statement', 'tag')

    def __str__(self):
        return f"{self.statement.text} -> {self.tag.name}"

class ChatLog(models.Model):
    """
    Модель для хранения истории чата вопросов пользователей, до обучения модели.
    """
    user_message = models.TextField(verbose_name="Сообщение пользователя")
    bot_response = models.TextField(verbose_name="Ответа бота")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата сообщения")
    is_training_pair = models.BooleanField(default=False, verbose_name="Дообучение бота")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Лог чата"
        verbose_name_plural = "Логи чата"

    def __str__(self):
        return f"[{self.created_at}] User: {self.user_message[:30]} | Bot: {self.bot_response[:30]}"


class TrainingPair(models.Model):
    """
    Модель для ручного до обучения модели.
    """
    question = models.TextField(verbose_name="Вопрос")
    answer = models.TextField(verbose_name="Ответ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_applied = models.BooleanField(default=False, verbose_name="Применено к боту")

    class Meta:
        verbose_name = "Обучающая пара"
        verbose_name_plural = "Обучающие пары"

    def __str__(self):
        return f"{self.question} -> {self.answer}"

