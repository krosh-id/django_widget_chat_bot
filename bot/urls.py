from django.urls import path, include
from bot.views import LibPageAPI

# апи для страницы библиотеки
extra_lib_patterns = [
    path('list_question/', LibPageAPI.as_view({'get': 'retrieve'})),
    path('form/', LibPageAPI.as_view({'post': 'create'})),
    path('predict_answer/', LibPageAPI.as_view({'post': 'get_response'})),
]

# основной патерн включающие другие патерны апи для страниц
urlpatterns = [
    path('lib/', include(extra_lib_patterns))
]
