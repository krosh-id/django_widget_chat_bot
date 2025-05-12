# Handlers for logic of processing social media messages
from django.core.cache import cache
from bs4 import BeautifulSoup
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from bot.models import Category, QuestionTopicNotification
from bot.serializers import CategorySerializer, QuestionTopicNotificationSerializer, FormQuestionSerializer
from bot.views import BaseCategoryQuestionAPIListCreate
import re
CLEANR = re.compile('<.*?>')

class VkMethod:
    page = 1
    vk = None
    answers = {}
    timeout_cache = 3600
    category_notification = []

    # Клавиатура меню
    keyboard_MENU = VkKeyboard(one_time=False)
    keyboard_MENU.add_button('Главное меню', color=VkKeyboardColor.POSITIVE)
    keyboard_MENU.add_line()
    keyboard_MENU.add_button('Задать другой вопрос', color=VkKeyboardColor.SECONDARY)

    # Клавиатура после действия "Задать другой вопрос"
    keyboard_PREFORM = VkKeyboard(one_time=False)
    keyboard_PREFORM.add_button('Отмена', color=VkKeyboardColor.NEGATIVE)
    keyboard_PREFORM.add_button('Продолжить', color=VkKeyboardColor.POSITIVE)

    # Клавиатура формы
    keyboard_FORM = VkKeyboard(one_time=True)
    keyboard_FORM.add_button('Отправить')
    keyboard_FORM.add_line()
    keyboard_FORM.add_button('Отмена', color=VkKeyboardColor.NEGATIVE)

    # Клавиатура выбора категория обращения в форме
    keyboard_CATEGORY_FORM = VkKeyboard(one_time=False)

    # Кнопка отмены
    keyboard_CANCEL = VkKeyboard(one_time=False)
    keyboard_CANCEL.add_button('Отмена')

    def __init__(self, vk_session):
        self.vk = vk_session.get_api()

    def __lists_and_paragraphs_to_text(self, html):
        soup = BeautifulSoup(html, "html.parser")

        # Обработка абзацев
        for p in soup.find_all('p'):
            p.insert_before("\n")
            p.insert_after("\n")

        # Обработка маркированных списков
        for ul in soup.find_all('ul'):
            items = [li.get_text() for li in ul.find_all('li')]
            ul.replace_with("\n".join(items) + "\n")

        # Обработка нумерованных списков
        for ol in soup.find_all('ol'):
            items = [f"{i + 1}. {li.get_text()}" for i, li in enumerate(ol.find_all('li'))]
            ol.replace_with("\n".join(items) + "\n")

        # Обработка ссылок
        for a in soup.find_all('a'):
            link_text = a.get_text()
            href = a.get('href')
            a.replace_with(f"{link_text}({href})")

        return soup.get_text()

    # !add cache
    def get_questions(self) -> list[dict]:
        """
        Получение вопросов по категориям из БД
        """
        queryset = Category.objects.filter(page_id=self.page).prefetch_related('questions').all()
        serializer = CategorySerializer(queryset, many=True)
        return serializer.data

    def get_notifications_cat(self):
        queryset = QuestionTopicNotification.objects.filter(page_id=self.page).all()
        serializer = QuestionTopicNotificationSerializer(queryset, many=True)
        return serializer.data

    def send_msg(self, user_id, text):
        """
        Отправка сообщения без клавиатуры
        """
        self.vk.messages.send(user_id=user_id, message=text, random_id=0)

    def send_msg_keyboard(self, user_id, keyboard, text=None) -> None:
        """
        Отправка сообщения с клавиатурой
        """
        self.vk.messages.send(user_id=user_id, message=text, random_id=0, keyboard=keyboard.get_keyboard())

    # Отправление стикеров
    def send_stick(self, user_id, number) -> None:
        self.vk.messages.send(user_id=user_id, sticker_id=number, random_id=0)

    def send_form(self, user_id, msg):
        """
        Отправка формы с анкетой и кнопками Отправить|Отмена
        """
        match msg:
            case 'продолжить':
                self.send_msg(user_id, 'Хорошо. Сейчас я задам несколько вопросов.')
            case 'отмена':
                cache.delete(f'user_data_{user_id}')  # Удаляем все данные пользователя
                cache.delete(f'user_step_{user_id}')
                self.send_main_menu(user_id)
                return
            case 'отправить':
                user_data = cache.get(f'user_data_{user_id}')
                user_data['page'] = self.page
                if not user_data or len(user_data) < 3:
                    self.send_msg(user_id, 'Анкета заполнена не полностью! Заполните все поля.')
                    return
                user_data['topic_question'] = QuestionTopicNotification.objects.filter(page_id=self.page).get(topic=user_data['topic_question']).id
                serializer = FormQuestionSerializer(data=user_data)

                if serializer.is_valid():
                    serializer.save()
                    BaseCategoryQuestionAPIListCreate.send_notifications_by_email(serializer.data, "vk.com")
                    self.send_msg(user_id, 'Ваше обращение успешно отправлено. Ожидайте ответа.')
                    cache.delete(f'user_data_{user_id}')
                    cache.delete(f'user_step_{user_id}')
                    self.send_main_menu(user_id)
                else:
                    self.send_msg(user_id, 'Ошибка при отправке анкеты. Попробуйте позже.')
                    cache.delete(f'user_data_{user_id}')
                    cache.delete(f'user_step_{user_id}')
                    self.send_main_menu(user_id)
                return

        step = cache.get_or_set(f'user_step_{user_id}', 0)
        user_data = cache.get_or_set(f'user_data_{user_id}', {})  # Получаем или создаем словарь данных

        match step:
            case 0:
                self.send_msg_keyboard(user_id, self.keyboard_CANCEL, 'Напиши своё ФИО в формате:\n'
                                                                      'Иванов Иван Иванович')
                cache.set(f'user_step_{user_id}', 1)
            case 1:
                pattern = r'^[A-Za-zА-Яа-яЁё\-\s]+$'
                if bool(re.match(pattern, msg)):
                    user_data['full_name'] = msg  # Сохраняем ФИО
                    cache.set(f'user_data_{user_id}', user_data)
                    cache.set(f'user_step_{user_id}', 2)
                    self.send_msg_keyboard(user_id, self.keyboard_CANCEL,
                                           'Теперь ты можешь указать свой номер телефона в формате: \n +7хххххххххх')
            case 2:
                pattern = r'^(\+7|8)\d{10}$'
                if bool(re.match(pattern, msg)):
                    user_data['mobile_phone'] = msg  # Сохраняем номер телефона
                    cache.set(f'user_data_{user_id}', user_data)
                    cache.set(f'user_step_{user_id}', 3)
                    self.send_msg_keyboard(user_id, self.keyboard_CANCEL, 'Укажи свою электронную почту')
            case 3:
                pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
                if bool(re.match(pattern, msg)):
                    user_data['email'] = msg  # Сохраняем email
                    cache.set(f'user_data_{user_id}', user_data)
                    cache.set(f'user_step_{user_id}', 4)
                    self.send_msg_keyboard(user_id, self.keyboard_CANCEL, 'Напиши свой вопрос и я его обязательно передам')
            case 4:
                if len(msg) < 450:
                    user_data['text'] = msg
                    cache.set(f'user_data_{user_id}', user_data)
                    cache.set(f'user_step_{user_id}', 5)

                    self.category_notification = self.get_notifications_cat()
                    for category in self.category_notification:
                        self.keyboard_CATEGORY_FORM.add_button(category['topic'])
                    self.send_msg_keyboard(user_id, self.keyboard_CATEGORY_FORM,
                                           'Выбери подходящую категорию для твоего вопроса с помощью кнопок')
                else:
                    self.send_msg(user_id, 'Сообщение слишком длинное, напиши короче')
            case 5:
                for category in self.category_notification:
                    if msg == category['topic'].lower():
                        user_data['topic_question'] = category['topic']  # Сохраняем категорию обращения
                        cache.set(f'user_data_{user_id}', user_data)
                        text = '\n'
                        for key in user_data.keys():
                            text += user_data[key] + '\n'
                        self.send_msg_keyboard(user_id, self.keyboard_FORM,
                                               f'Проверьте ваши данные: {text}')
                        break
                else:
                    self.send_msg(user_id, 'Выберите категорию обращения с помощью кнопок')

    def send_main_menu(self, user_id: int) -> None:
        """
        Отправка сообщение со списком вопросов по категориям
        """
        categories  = self.get_questions()
        text = ''

        i = 1
        for category in categories:
            text += 'ᅠ ᅠ ᅠ ᅠ 📝' + category['name'] + '📝' + '\n'
            for question in category['questions']:
                text += f'{i}) '+ question['text'] + '\n'
                answer_db = question['answer']
                if '<' in answer_db:
                    self.answers[i] = self.__lists_and_paragraphs_to_text(answer_db)
                i += 1

        self.send_msg_keyboard(user_id, self.keyboard_MENU, text)

    def send_answer(self, user_id: int, question_id: int):
        if question_id in self.answers:
            self.send_msg_keyboard(user_id, self.keyboard_MENU, self.answers[question_id])
        else:
            self.send_msg_keyboard(user_id,
                                   self.keyboard_MENU,
                                   'Я не знаю ответа на такой вопрос. Введите номер из списка')
