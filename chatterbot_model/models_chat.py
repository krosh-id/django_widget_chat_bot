from chatterbot import ChatBot
from chatterbot.trainers import JsonFileTrainer
from chatterbot_model.models import ChatLog


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

    def get_answer(self, text: str) -> str:
        print(f"[user]: {text}")
        answer = str(self.bot.get_response(text))
        print(f"[bot]: {answer}")

        # Логирование
        try:
            ChatLog.objects.create(
                user_message=text,
                bot_response=answer
            )
        except Exception as e:
            print(f"⚠️ Ошибка логирования чата: {e}")

        return answer


class LibraryBotModel(CommonBotModel):
    _instance = None  # Атрибут класса для Singleton

    def __init__(self,
                 uri_db: str = "postgresql://chatbot_user:root@localhost:5432/model_chatbot_db",
                 directory_json: str = "./chatterbot_model/data/training_data.json",
                 train: bool = False):
        # Родительский init запускается только при первом создании экземпляра
        super().__init__(uri_db=uri_db, directory_json=directory_json, train=train)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            print("🟢 Инициализация Singleton LibraryBotModel")
            cls._instance = cls()
        return cls._instance
