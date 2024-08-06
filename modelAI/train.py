import random
import pickle
import json
from nltk.tokenize import word_tokenize
from keras.api.optimizers import SGD
from keras.api.layers import Dense, Dropout
from keras.api.models import Sequential
import numpy as np
import pymorphy3

# Инициализация переменных
words = []
classes = []
documents = []
ignore_words = ["?", "!", ".", ","]

# Инициализация лемматизатора pymorphy2
morph = pymorphy3.MorphAnalyzer()

# Загрузка намерений из JSON файла
with open("D:/labs/widget_bot_pskgu/widget/modelAI/intents.json", encoding="utf-8") as file:
    intents = json.load(file)

# Обработка данных
for intent in intents["intents"]:
    for pattern in intent["patterns"]:
        # Токенизация слов
        w = word_tokenize(pattern)
        words.extend(w)
        documents.append((w, intent["tag"]))
        if intent["tag"] not in classes:
            classes.append(intent["tag"])

# Лемматизация и удаление стоп-слов
words = [morph.parse(w.lower())[0].normal_form for w in words if w not in ignore_words]
words = sorted(list(set(words)))
classes = sorted(list(set(classes)))

print(len(documents), "documents")
print(len(classes), "classes", classes)
print(len(words), "unique lemmatized words", words)

# Сохранение слов и классов в pickle файлы
pickle.dump(words, open("words.pkl", "wb"))
pickle.dump(classes, open("classes.pkl", "wb"))

# Инициализация тренировочных данных
training = []
output_empty = [0] * len(classes)
for doc in documents:
    bag = []
    pattern_words = doc[0]
    pattern_words = [morph.parse(word.lower())[0].normal_form for word in pattern_words]
    for w in words:
        bag.append(1) if w in pattern_words else bag.append(0)
    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1
    training.append([bag, output_row])

# Перемешивание и конвертация в массивы NumPy
random.shuffle(training)
train_x = np.array([item[0] for item in training])
train_y = np.array([item[1] for item in training])

print("Training data created")

# Создание модели
model = Sequential()
model.add(Dense(128, input_shape=(len(train_x[0]),), activation="relu"))
model.add(Dropout(0.5))
model.add(Dense(64, activation="relu"))
model.add(Dropout(0.5))
model.add(Dense(len(train_y[0]), activation="softmax"))
model.summary()

# Компиляция модели
sgd = SGD(learning_rate=0.01, momentum=0.9, nesterov=True)
model.compile(loss="categorical_crossentropy", optimizer=sgd, metrics=["accuracy"])

# Обучение и сохранение модели
hist = model.fit(train_x, train_y, epochs=200, batch_size=5, verbose=1)
model.save("chatbot_model.keras", hist)
print("Model created")
