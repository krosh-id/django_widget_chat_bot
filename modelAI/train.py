import random
import pickle
import json

import nltk
from keras.optimizer_v2.gradient_descent import SGD
from nltk.tokenize import word_tokenize

from keras.layers import Dense, Dropout, BatchNormalization
from keras.models import Sequential
import numpy as np
import pymorphy3
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import classification_report
from sklearn.utils import shuffle

# Инициализация переменных
words = []
classes = []
documents = []
ignore_words = ["?", "!", ".", ","]

# Инициализация лемматизатора pymorphy3
morph = pymorphy3.MorphAnalyzer()
nltk.download('punkt')
nltk.download("wordnet")

# Загрузка намерений из JSON файла
with open("D:/labs/django_widget_chat_bot/modelAI/intents.json", encoding="utf-8") as file:
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
print(len(words), "unique lemmatized words")

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
    bag = [1 if w in pattern_words else 0 for w in words]
    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1
    training.append([bag, output_row])

# Перемешивание и конвертация в массивы NumPy
random.shuffle(training)
train_x = np.array([item[0] for item in training])
train_y = np.array([item[1] for item in training])

# Кросс-валидация: 5 фолдов
kf = KFold(n_splits=5, shuffle=True, random_state=42)

# Массив для хранения результатов
accuracy_per_fold = []
classification_reports = []

# Создаем модель вне цикла
model = Sequential()
model.add(Dense(256, input_shape=(len(train_x[0]),), activation="relu"))
model.add(BatchNormalization())  # Улучшение устойчивости
model.add(Dropout(0.5))
model.add(Dense(128, activation="relu"))
model.add(BatchNormalization())
model.add(Dropout(0.5))
model.add(Dense(len(train_y[0]), activation="softmax"))
model.summary()

# Компиляция модели
sgd = SGD(learning_rate=0.01, momentum=0.9, nesterov=True)
model.compile(loss="categorical_crossentropy", optimizer=sgd, metrics=["accuracy"])

for fold, (train_index, val_index) in enumerate(kf.split(train_x)):
    print(f"\nProcessing fold {fold + 1}...")

    # Разделение данных на текущую обучающую и валидационную выборки
    X_train, X_val = train_x[train_index], train_x[val_index]
    y_train, y_val = train_y[train_index], train_y[val_index]

    # Обучение модели
    hist = model.fit(X_train, y_train, epochs=100, batch_size=8, verbose=1, validation_data=(X_val, y_val))

    # Оценка модели
    y_pred = model.predict(X_val, batch_size=8)  # Оптимизация с батчами
    y_pred_classes = np.argmax(y_pred, axis=1)
    y_val_classes = np.argmax(y_val, axis=1)

    # Получаем метрики
    accuracy = np.mean(y_pred_classes == y_val_classes)
    accuracy_per_fold.append(accuracy)

    # Получаем отчёт по F1, Precision, Recall и другие метрики
    labels = list(range(len(classes)))  # Метки от 0 до количества классов
    report = classification_report(y_val_classes, y_pred_classes, zero_division=1, target_names=classes, labels=labels)
    classification_reports.append(report)

    print(f"Fold {fold + 1} - Accuracy: {accuracy:.4f}")
    print(f"Fold {fold + 1} - Classification Report:\n {report}")

# Рассчитываем среднюю точность по всем фолдам
average_accuracy = np.mean(accuracy_per_fold)
print(f"\nAverage Accuracy across all folds: {average_accuracy:.4f}")

# Сохранение модели (последней модели из последнего фолда)
model.save("chatbot_model.keras")
print("Model created")
