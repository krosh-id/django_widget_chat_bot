from django.contrib.auth import get_user_model
from django.db import models
from ckeditor.fields import RichTextField

class Page(models.Model):
    name = models.CharField(max_length=255, null=False, verbose_name="Название страницы")
    url = models.URLField(null=False, unique=True, verbose_name="Адрес страницы")
    slug = models.SlugField(max_length=100, unique=True)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255, null=False, verbose_name="Название категории")
    created_by = models.ForeignKey(get_user_model(),
                                   on_delete=models.CASCADE,
                                   related_name='categories',
                                   verbose_name="Создатель категории")
    page = models.ForeignKey(Page,
                             on_delete=models.PROTECT,
                             related_name='categories',
                             verbose_name="Отношение к странице")

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Question(models.Model):
    class Status(models.IntegerChoices):
        DRAFT = 0, 'Черновик'
        PUBLISHED = 1, 'Опубликовано'

    text = models.CharField(verbose_name="Текст вопроса")
    answer = RichTextField(verbose_name="Ответ на вопрос")
    created_by = models.ForeignKey(get_user_model(),
                                   on_delete=models.CASCADE,
                                   related_name='questions',
                                   verbose_name="Создатель вопроса")
    category = models.ForeignKey(Category,
                                 on_delete=models.CASCADE,
                                 related_name='questions',
                                 verbose_name="Категория")
    is_published = models.BooleanField(choices=tuple(map(lambda x: (bool(x[0]), x[1]), Status.choices)),
                                       default=Status.PUBLISHED,
                                       verbose_name="Статус")
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    date_modified = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return self.text


class QuestionTopicNotification(models.Model):
    topic = models.CharField(max_length=55, verbose_name="Тема обращения", null=False)
    send_to_email = models.EmailField(max_length=100, verbose_name="Почта для уведомлений")
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='question_topics',
                             verbose_name="Отношение к странице")

    class Meta:
        verbose_name = 'Тема обращения'
        verbose_name_plural = 'Темы обращения'

    def __str__(self):
        return self.topic


class FormQuestion(models.Model):
    full_name = models.CharField(max_length=255, verbose_name="Полное имя", null=False)
    mobile_phone = models.CharField(max_length=55, verbose_name="Номер телефона", null=True)
    email = models.EmailField(verbose_name="Эл. почта", null=False)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    text = models.CharField(max_length=500, verbose_name="Текст обращения", null=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='form_questions',
                             verbose_name="Отношение к странице")
    topic_question = models.ForeignKey(QuestionTopicNotification,
                                       related_name='question_topic_notifications',
                                       on_delete=models.CASCADE,
                                       verbose_name="Тема обращения",
                                       )

    class Meta:
        verbose_name = 'Обращение'
        verbose_name_plural = 'Обращения'
        ordering = ['-date_created']
        default_permissions = ('view',)

    def __str__(self):
        return self.email + ': ' + self.full_name + str(self.date_created)
