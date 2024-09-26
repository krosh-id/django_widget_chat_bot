from django.urls import path, include
from bot.custom_admin import CheckCreateAdminPage
from bot.views import LibPageAPI

extra_admin_site_patterns = []
extra_admin_site_patterns.extend(CheckCreateAdminPage().main())

# апи для страницы библиотеки
extra_lib_patterns = [
    path('list_question/', LibPageAPI.as_view({'get': 'retrieve'})),
    path('form/', LibPageAPI.as_view({'post': 'create'})),
    path('predict_answer/', LibPageAPI.as_view({'post': 'get_response'})),
    path('get_history', LibPageAPI.as_view({'get': 'get_history'}))
]

# основной патерн включающие другие патерны страниц
urlpatterns = [
    path('widget_admin/', include(extra_admin_site_patterns)),
    path('api/lib/', include(extra_lib_patterns)),
]
