from decouple import config
from chatterbot import ChatBot
from chatterbot.trainers import JsonFileTrainer, ListTrainer
from chatterbot_model.models import ChatLog, TrainingPair, Statement, Tag, TagAssociation
import logging

logging.basicConfig(filename='chatterbot.log', level=logging.INFO, format='%(asctime)s - %(message)s', encoding="utf-8")

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

    def train_from_json(self, bot: ChatBot, directory: str):
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

    def reset_model(self, json_directory: str):
        """
        Сбрасывает данные обучения бота и переобучает его из JSON-файла.
        """
        try:
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