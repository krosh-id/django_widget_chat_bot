import json
import random
import numpy as np
import pickle
import nltk
from keras.api.keras.models import load_model
import pymorphy3


class ChatPredict:

    def __init__(self,  # Исправлено: __init__ вместо init
                 model_dir: str,
                 words_dir: str,
                 classes_dir: str,
                 intents_dir: str):
        """
        Служит для предсказания ответов на основе существующей обученной модели.

        :param model_dir:
        :param words_dir:
        :param classes_dir:
        :param intents_dir:
        """
        # Загрузка обученной модели и данных
        self.model = load_model(model_dir)  # .keras
        self.words = pickle.load(open(words_dir, "rb"))
        self.classes = pickle.load(open(classes_dir, "rb"))
        self.intents = json.loads(open(intents_dir, encoding="utf-8").read())  # .json

        # Инициализация лемматизатора pymorphy2
        self.morph = pymorphy3.MorphAnalyzer()

    def clean_up_sentence(self, sentence):
        sentence_words = nltk.word_tokenize(sentence, language='russian')
        return [self.morph.parse(word.lower())[0].normal_form for word in sentence_words]

    def __bow(self, sentence, words, show_details=False):
        sentence_words = self.clean_up_sentence(sentence) # Исправлено: self.clean_up_sentence
        bag = [0] * len(words)
        for s in sentence_words:
            for i, w in enumerate(words):
                if w == s:
                    bag[i] = 1
                    if show_details:
                        print(f"found in bag: {w}")
        return np.array(bag)

    def __predict_class(self, sentence, model):
        p = self.__bow(sentence, self.words, show_details=False)
        p = np.array([p])
        res = model.predict(p, verbose=0)[0]
        error_threshold = 0.25
        results = [[i, r] for i, r in enumerate(res) if r > error_threshold]
        results.sort(key=lambda x: x[1], reverse=True)
        return results # Возвращаем results, даже если он пустой

    def __get_response(self, ints):
        if not ints:  # Проверка на пустой список
            return "Извини, я тебя не понимаю." # Добавлено сообщение об ошибке
        tag = ints[0][0] # Исправлено: индекс 0 для получения тега
        for i in self.intents["intents"]:
            if i["tag"] == self.classes[tag]: # Исправлено: используется self.classes[tag]
                return random.choice(i["responses"])
        return "Извини, я не знаю ответа на этот вопрос." # Добавлено сообщение об отсутствии ответа

    def get_answer(self, msg):
        ints = self.__predict_class(msg, self.model)
        res = self.__get_response(ints)
        return res


class LibChatPredict(ChatPredict):
    def __init__(self,
                 model_dir: str = "D:/labs/django_widget_chat_bot/modelAI/chatbot_model.keras",
                 words_dir: str = "D:/labs/django_widget_chat_bot/modelAI/words.pkl",
                 classes_dir: str = "D:/labs/django_widget_chat_bot/modelAI/classes.pkl",
                 intents_dir: str = "D:/labs/django_widget_chat_bot/modelAI/intents.json"):
        """
        Служит для предсказания ответов на основе существующей обученной модели для библиотеки.

        :param model_dir: путь к модели
        :param words_dir: путь к словам
        :param classes_dir: путь к классам
        :param intents_dir: путь к намерениям
        """

        super().__init__(model_dir, words_dir, classes_dir, intents_dir) # Исправлено: __init__