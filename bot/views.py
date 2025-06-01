import re
from django.utils.decorators import method_decorator, decorator_from_middleware
from django.views.decorators.cache import cache_page
from django.core.mail import send_mail
from django_ratelimit.decorators import ratelimit
from rest_framework.response import Response
from rest_framework import viewsets, status
from bot.models import Category, Page, QuestionTopicNotification
from bot.request_log.middleware import RequestLogMiddleware
from bot.serializers import CategorySerializer, FormQuestionSerializer, QuestionTopicNotificationSerializer
from chatterbot_model.models_chat import LibraryBotModel
import logging

logger = logging.getLogger('bot')
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

    def __init__(self, class_chatbot_model, page_id: int):
        if 'get_answer' not in dir(class_chatbot_model) or not class_chatbot_model:
            raise ValueError('Используйте класс на основе ChatPredict')
        try:
            page = Page.objects.get(pk=page_id)
        except Page.DoesNotExist:
            raise ValueError(f'Страницы с айди {page_id} не существует')

        self.model_chat = class_chatbot_model
        self.page_id = page_id
        self.page_url = page.url
        super().__init__()

    @staticmethod
    def __sanitize_message(msg):
        """Очистка сообщения от опасного содержимого."""
        # Убираем потенциально опасные теги
        msg = re.sub(r'<[^>]*>', '', msg)
        # Убираем лишние пробелы
        msg = msg.strip()
        return msg

    @staticmethod
    def send_notifications_by_email(data: dict, page_url: str):
        try:
            notification = QuestionTopicNotification.objects.get(pk=data['topic_question'])
            for email in notification.send_to_email:
                send_mail(
                    f"Новый вопрос по теме {notification.topic}",
                    f"""
                                    Появился новый вопрос на странице {page_url}.
                                    Содержание вопроса:
                                        "{data['text']}"
                                    От: {data['full_name']} {data['email']}
    
                                    Вы получили это письмо так как подписаны на рассылку уведомлений. 
                                    Не нужно отвечать на это письмо!
                                """,
                    "widgetbot@yandex.ru",
                    [email],
                    fail_silently=False,
                )
        except Exception as e:
            logger.error(f"Exception in send_by_email: {str(e)}", exc_info=True)
            return Response({'error': 'Error send by email'}, status=status.HTTP_400_BAD_REQUEST)


    # 2 отдельных SQL запроса на категории и вопросы
    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    @method_decorator(cache_page(60 * 60, key_prefix='category_questions_{}'.format(page_id)))
    def retrieve(self, request):
        queryset = Category.objects.filter(page_id=self.page_id).prefetch_related('questions').all()
        serializer = CategorySerializer(queryset, many=True)

        return Response(serializer.data)

    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    def create(self, request):
        try:
            serializer = FormQuestionSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                self.send_notifications_by_email(serializer.data, self.page_url)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Exception in create form: {str(e)}", exc_info=True)
            return Response({'error': 'Error create form'}, status=status.HTTP_400_BAD_REQUEST)


    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    #@csrf_protect
    def get_response(self, request):
        # Безопасно получаем и валидируем сообщение
        msg = request.data.get('msg')

        if not isinstance(msg, str) or len(msg) > 1000:
            return Response({'error': 'Некорректное сообщение'}, status=status.HTTP_400_BAD_REQUEST)

        # Дополнительная защита от возможных вредоносных данных
        msg = self.__sanitize_message(msg)

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
        queryset = QuestionTopicNotification.objects.filter(page_id=self.page_id).all()
        serializer = QuestionTopicNotificationSerializer(queryset, many=True)
        return Response(serializer.data)



class LibPageAPI(BaseCategoryQuestionAPIListCreate):
    def __init__(self):
        super().__init__(class_chatbot_model=LibraryBotModel.get_instance(), page_id=1)

