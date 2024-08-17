from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.response import Response
from rest_framework import viewsets, status
import bot.models
from bot.chat_predict import LibChatPredict
from bot.models import Category, Page
from bot.serializers import CategorySerializer, FormQuestionSerializer


class BaseCategoryQuestionAPIListCreate(viewsets.ViewSet):
    """
        Представление для получения списка вопросов по категориям по методу retrieve,
        создание нового обращения пользователям по методу create,
        получение ответа на основе модели nltk и метода get_response

        :param model_chat: объект чата модели основанный на ChatPredict
        :param page_id: айди страницы из бд к которой будет привязан чат бот
    """
    model_chat = None
    page_id = None

    def __init__(self, class_chat_predict, page_id: int):
        if 'get_answer' not in dir(class_chat_predict) or not class_chat_predict:
            raise ValueError('Используйте класс на основе ChatPredict')
        try:
            Page.objects.get(pk=page_id)
        except bot.models.Page.DoesNotExist:
            raise ValueError(f'Страницы с айди {page_id} не существует')

        self.model_chat = class_chat_predict
        self.page_id = page_id
        super().__init__()

    # 2 отдельных sql запроса на категории и вопросы
    @method_decorator(cache_page(60*60), name='list_question')
    def retrieve(self, request):
        queryset = Category.objects.filter(page_id=self.page_id).prefetch_related('questions').all()
        serializer = CategorySerializer(queryset, many=True)

        return Response(serializer.data)

    def create(self, request):
        serializer = FormQuestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_response(self, request):
        msg = request.data.get('msg', 'пока')
        if msg.startswith(('меня зовут', 'привет, меня зовут')):
            name = msg.split()[-1]
            res = self.model_chat.get_answer(msg).replace("{n}", name)
        else:
            res = self.model_chat.get_answer(msg)

        return Response({'answer': res})


class LibPageAPI(BaseCategoryQuestionAPIListCreate):
    def __init__(self):
        class_chat_predict = LibChatPredict()
        page_id = 2
        super().__init__(class_chat_predict, page_id)
