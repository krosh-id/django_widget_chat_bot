import re
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_protect
from django_ratelimit.decorators import ratelimit
from rest_framework.response import Response
from rest_framework import viewsets, status
from bot.chat_predict import LibChatPredict
from bot.models import Category, Page
from bot.serializers import CategorySerializer, FormQuestionSerializer


class BaseCategoryQuestionAPIListCreate(viewsets.ViewSet):
    """
        Представление для получения списка вопросов по категориям по методу retrieve,
        создание нового обращения пользователям по методу create,
        получение ответа на основе модели nltk и метода get_response
    """
    model_chat = None
    page_id = None

    def __init__(self, class_chat_predict, page_id: int):
        if 'get_answer' not in dir(class_chat_predict) or not class_chat_predict:
            raise ValueError('Используйте класс на основе ChatPredict')
        try:
            Page.objects.get(pk=page_id)
        except Page.DoesNotExist:
            raise ValueError(f'Страницы с айди {page_id} не существует')

        self.model_chat = class_chat_predict
        self.page_id = page_id
        super().__init__()

    @staticmethod
    def sanitize_message(msg):
        """Очистка сообщения от опасного содержимого."""
        # Убираем потенциально опасные теги
        msg = re.sub(r'<[^>]*>', '', msg)
        # Убираем лишние пробелы
        msg = msg.strip()
        return msg

    @staticmethod
    def __get_chat_history(request):
        return request.session.get('chat_history', [])

    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    def get_history(self, request):
        # Получаем историю чата из сессии, если она существует
        return Response(self.__get_chat_history(request))

    # 2 отдельных SQL запроса на категории и вопросы
    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    @method_decorator(cache_page(60 * 60, key_prefix='category_questions_{}'.format(page_id)))
    def retrieve(self, request):
        queryset = Category.objects.filter(page_id=self.page_id).prefetch_related('questions').all()
        serializer = CategorySerializer(queryset, many=True)

        return Response(serializer.data)

    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    @csrf_protect
    def create(self, request):
        serializer = FormQuestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @method_decorator(ratelimit(key='user_or_ip', rate='10/m'))
    #@csrf_protect
    def get_response(self, request):
        # Безопасно получаем и валидируем сообщение
        msg = request.data.get('msg', 'пока')

        if not isinstance(msg, str) or len(msg) > 1000:
            return Response({'error': 'Некорректное сообщение'}, status=status.HTTP_400_BAD_REQUEST)

        # Дополнительная защита от возможных вредоносных данных
        msg = self.sanitize_message(msg)

        chat_history = self.__get_chat_history(request)
        chat_history.append({'user': msg})

        # Логика обработки имени
        if msg.startswith(('меня зовут', 'привет, меня зовут')):
            name = msg.split()[-1]
            if re.match(r'^[A-Za-zА-Яа-я]{2,50}$', name):  # Проверяем, что имя корректно
                res = self.model_chat.get_answer(msg).replace("{n}", name)
            else:
                res = "Некорректное имя."
        else:
            res = self.model_chat.get_answer(msg)

        chat_history.append({'bot': res})
        request.session['chat_history'] = chat_history
        return Response({'answer': res})


class LibPageAPI(BaseCategoryQuestionAPIListCreate):
    def __init__(self):
        class_chat_predict = LibChatPredict()
        page_id = 1
        super().__init__(class_chat_predict, page_id)
