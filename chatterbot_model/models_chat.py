import json
import os

from decouple import config
from chatterbot import ChatBot
from chatterbot.trainers import JsonFileTrainer, ListTrainer

from bot.models import Question
from chatterbot_model.models import ChatLog, TrainingPair, Statement, Tag, TagAssociation
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger('chatterbot')

# Предопределённая фраза и порог уверенности
DEFAULT_RESPONSE = ("Я не chatgpt и могу отвечать только на определенные вопросы 😊. "
                    "Если ты не нашёл ответ обратись в раздел 'Вопросы'. Там ты можешь задать вопрос сотруднику")
CONFIDENCE_THRESHOLD = 0.4

class CommonBotModel:
    def __init__(self,
                 uri_db: str,
                 directory_json: str = None,
                 train: bool = False):
        self.bot = ChatBot(
            'FAQBot',
            read_only=True,
            storage_adapter="chatterbot.storage.SQLStorageAdapter",
            database_uri=uri_db
        )

        if train and directory_json:
            self.train_from_json(self.bot, directory_json)
            print("Обучение прошло успешно")
            logging.info("Обучение прошло успешно")

        print('✅ Модель чата запущена!')

    @staticmethod
    def generate_training_json(json_path: str = "./chatterbot_model/data/training_data.json"):
        """
        Формирует JSON-файл в формате ChatterBot на основе вопросов и обучающих пар.
        """
        try:
            # Удаляем старый JSON-файл, если существует
            if os.path.exists(json_path):
                os.remove(json_path)
                logging.info(f"🧹 Старый JSON-файл удалён: {json_path}")
            conversation = []

            # Вопросы из модели Question
            questions = Question.objects.filter(is_published=True)
            for q in questions:
                category = q.category.name.strip()
                clean_q = BeautifulSoup(q.text, features="lxml").text.strip()
                clean_a = BeautifulSoup(q.answer, features="lxml").text.strip()

                # User сообщение
                conversation.append({
                    "text": clean_q,
                    "in_response_to": None,
                    "persona": "user",
                    "conversation": category,
                    "tags": [category]
                })

                # Ответ бота
                conversation.append({
                    "text": clean_a,
                    "in_response_to": clean_q,
                    "persona": "bot",
                    "conversation": category,
                    "tags": [category]
                })

            # Обучающие пары из TrainingPair
            training_pairs = TrainingPair.objects.filter(is_applied=False)
            for pair in training_pairs:
                category = "Другие вопросы"

                conversation.append({
                    "text": pair.question.strip(),
                    "in_response_to": None,
                    "persona": "user",
                    "conversation": category,
                    "tags": [category]
                })

                conversation.append({
                    "text": pair.answer.strip(),
                    "in_response_to": pair.question.strip(),
                    "persona": "bot",
                    "conversation": category,
                    "tags": [category]
                })

            # Запись в JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({"conversation": conversation}, f, ensure_ascii=False, indent=4)

            logging.info(f"✅ Сформирован JSON-файл обучения: {json_path}")
            return json_path

        except Exception as e:
            logging.error(f"❌ Ошибка при генерации JSON-файла: {e}")
            raise

    @staticmethod
    def train_from_json(bot: ChatBot, directory: str):
        trainer = JsonFileTrainer(
            bot,
            field_map={
                'text': 'text',
                'in_response_to': 'in_response_to',
                'persona': 'persona',
                'conversation': 'conversation',
                'tags': 'tags'
            }
        )
        trainer.train(directory)
        print('✅ Обучение произошло успешно')
        logging.info('✅ Обучение произошло успешно')

    def reset_model(self, json_directory: str = None):
        """
        Сбрасывает данные обучения бота и переобучает его из JSON-файла.
        """
        try:
            if not json_directory:
                print('обучение моедли--------')
                json_directory = str(self.generate_training_json())
                print(json_directory)

            # Создаём временный бот для сброса и переобучения
            training_bot = ChatBot(
                'FAQBot',
                read_only=False,
                storage_adapter="chatterbot.storage.SQLStorageAdapter",
                database_uri=self.bot.storage.database_uri
            )

            TagAssociation.objects.using('chatbot').all().delete()
            logging.info("Модель TagAssociation очищена")

            Tag.objects.using('chatbot').all().delete()
            logging.info("Модель Tag очищена")

            Statement.objects.using('chatbot').all().delete()
            logging.info("Модель Statement очищена")

            # Очищаем ChatLog (только обучающие пары)
            ChatLog.objects.using('chatbot').filter(is_training_pair=True).delete()
            logging.info("Обучающие пары в ChatLog удалены")

            # Сбрасываем флаг is_applied в TrainingPair
            TrainingPair.objects.using('chatbot').update(is_applied=False)
            logging.info("Флаги is_applied в TrainingPair сброшены")

            # Переобучаем бота из JSON
            self.train_from_json(training_bot, json_directory)
            TrainingPair.objects.using('chatbot').update(is_applied=True)
            logging.info(f"Бот переобучен из JSON: {json_directory}")

            # Обновляем основной бот
            self.bot = ChatBot(
                'FAQBot',
                read_only=True,
                storage_adapter="chatterbot.storage.SQLStorageAdapter",
                database_uri=self.bot.storage.database_uri
            )
            logging.info("Основной бот обновлён")

        except Exception as e:
            print(e)
            logging.error(f"Ошибка при сбросе и переобучении модели: {e}")
            raise

    def train_from_pair(self, user_input: str, bot_response: str):
        training_bot = ChatBot(
            'FAQBot',
            read_only=False,
            storage_adapter="chatterbot.storage.SQLStorageAdapter",
            database_uri=self.bot.storage.database_uri
        )

        try:
            trainer = ListTrainer(training_bot)
            trainer.train([user_input, bot_response])
            print(f"✅ Бот дообучен на паре: '{user_input}' -> '{bot_response}'")
            logging.info(f"Бот дообучен на паре: '{user_input}' -> '{bot_response}'")

            ChatLog.objects.using('chatbot').create(
                user_message=user_input,
                bot_response=bot_response,
                is_training_pair=True
            )
            self.bot = ChatBot(
                'FAQBot',
                read_only=True,
                storage_adapter="chatterbot.storage.SQLStorageAdapter",
                database_uri=self.bot.storage.database_uri
            )
            logging.info("Основной бот обновлён")
        except Exception as e:
            print(f"⚠️ Ошибка при дообучении или логировании: {e}")
            logging.error(f"Ошибка при дообучении или логировании: {e}")
        finally:
            del training_bot

    def get_answer(self, text: str) -> str:
        print(f"[user]: {text}")
        response = self.bot.get_response(text)
        answer = str(response)

        # Проверяем уверенность ответа
        if response.confidence < CONFIDENCE_THRESHOLD:
            answer = DEFAULT_RESPONSE
            print(f"[bot]: {answer} (confidence: {response.confidence})")
            logging.info(f"Ответ не найден для '{text}', confidence: {response.confidence}, возвращена фраза: '{answer}'")
        else:
            print(f"[bot]: {answer} (confidence: {response.confidence})")
            logging.info(f"Ответ для '{text}': '{answer}', confidence: {response.confidence}")

        # Логирование в ChatLog
        try:
            ChatLog.objects.using('chatbot').create(
                user_message=text,
                bot_response=answer
            )
        except Exception as e:
            print(f"⚠️ Ошибка логирования чата: {e}")
            logging.error(f"Ошибка логирования чата: {e}")

        return answer


class LibraryBotModel(CommonBotModel):
    _instance = None  # Атрибут класса для Singleton

    def __init__(self,
                 uri_db: str = config('DATABASE_URI_CHATTERBOT'),
                 directory_json: str = "./chatterbot_model/data/training_data.json",
                 train: bool = False):
        # Родительский init запускается только при первом создании экземпляра
        super().__init__(uri_db=uri_db, directory_json=directory_json, train=train)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            print("🟢 Инициализация Singleton LibraryBotModel")
            logging.info("🟢 Инициализация Singleton LibraryBotModel")
            cls._instance = cls()
        return cls._instance