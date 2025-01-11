import re
from django.utils.decorators import method_decorator, decorator_from_middleware
from django.views.decorators.cache import cache_page
from django.core.mail import send_mail
from django_ratelimit.decorators import ratelimit
from rest_framework.response import Response
from rest_framework import viewsets, status
from bot.chat_predict import LibChatPredict
from bot.models import Category, Page, QuestionTopicNotification
from bot.request_log.middleware import RequestLogMiddleware
from bot.serializers import CategorySerializer, FormQuestionSerializer, QuestionTopicNotificationSerializer

request_log = decorator_from_middleware(RequestLogMiddleware)

class BaseCategoryQuestionAPIListCreate(viewsets.ViewSet):
    """
        Представление для получения списка вопросов по категориям по методу retrieve,
        создание нового обращения пользователям по методу create,
        получение ответа на основе модели nltk и метода get_response
    """
    model_chat = None
    page_id = None
    page_url = None

    def __init__(self, class_chat_predict, page_id: int):
        if 'get_answer' not in dir(class_chat_predict) or not class_chat_predict:
            raise ValueError('Используйте класс на основе ChatPredict')
        try:
            page = Page.objects.get(pk=page_id)
        except Page.DoesNotExist:
            raise ValueError(f'Страницы с айди {page_id} не существует')

        self.model_chat = class_chat_predict
        self.page_id = page_id
        self.page_url = page.url
        super().__init__()

    @staticmethod
    def sanitize_message(msg):
        """Очистка сообщения от опасного содержимого."""
        # Убираем потенциально опасные теги
        msg = re.sub(r'<[^>]*>', '', msg)
        # Убираем лишние пробелы
        msg = msg.strip()
        return msg

    # 2 отдельных SQL запроса на категории и вопросы
    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    @method_decorator(cache_page(60 * 60, key_prefix='category_questions_{}'.format(page_id)))
    def retrieve(self, request):
        queryset = Category.objects.filter(page_id=self.page_id).prefetch_related('questions').all()
        serializer = CategorySerializer(queryset, many=True)

        return Response(serializer.data)

    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    def create(self, request):
        serializer = FormQuestionSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            notification = QuestionTopicNotification.objects.get(pk=serializer.data['topic_question'])
            for email in notification.send_to_email:
                send_mail(
                    f"Новый вопрос по теме {notification.topic}",
                    f"""
                        Появился новый вопрос на странице {self.page_url}.
                        Содержание вопроса:
                            "{serializer.data['text']}"
                        От: {serializer.data['full_name']} {serializer.data['email']}
                        
                        Вы получили это письмо так как подписаны на рассылку уведомлений. 
                        Не нужно отвечать на это письмо!
                    """,
                    "widgetbot@yandex.ru",
                    [email],
                    fail_silently=False,
                )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    @request_log
    #@csrf_protect
    def get_response(self, request):
        # Безопасно получаем и валидируем сообщение
        msg = request.data.get('msg')

        if not isinstance(msg, str) or len(msg) > 1000:
            return Response({'error': 'Некорректное сообщение'}, status=status.HTTP_400_BAD_REQUEST)

        # Дополнительная защита от возможных вредоносных данных
        msg = self.sanitize_message(msg)

        # Логика обработки имени
        if msg.startswith(('меня зовут', 'привет, меня зовут')):
            name = msg.split()[-1]
            if re.match(r'^[A-Za-zА-Яа-я]{2,50}$', name):  # Проверяем, что имя корректно
                res = self.model_chat.get_answer(msg).replace("{n}", name)
            else:
                res = "Некорректное имя."
        else:
            res = self.model_chat.get_answer(msg)

        return Response({'answer': res})

    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    @method_decorator(cache_page(60 * 60, key_prefix='category_questions_{}'.format(page_id)))
    def get_question_topic(self, request):
        queryset = QuestionTopicNotification.objects.all()
        serializer = QuestionTopicNotificationSerializer(queryset, many=True)

        return Response(serializer.data)


class LibPageAPI(BaseCategoryQuestionAPIListCreate):
    def __init__(self):
        class_chat_predict = LibChatPredict()
        page_id = 1
        super().__init__(class_chat_predict, page_id)
