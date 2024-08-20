import requests
from django.urls import path, include
from bot.admin import create_custom_admin_site
from bot.models import Page
from bot.views import LibPageAPI

# автоматическое формирование админ страниц для Page
extra_admin_site_patterns = []
for page in Page.objects.all():
    response = requests.get(str(page.url))
    if response.status_code == 200:
        print(f'\033[32m Страница по адресу: {page.url} — активна \033[0m')
    else:
        print(f'\033[31m Страница по адресу: {page.url} — !не отвечает! \033[0m')

    admin_site = create_custom_admin_site(page.id, page.name, page.url)
    extra_admin_site_patterns.append(path(f'{page.slug}/', admin_site.urls))

# апи для страницы библиотеки
extra_lib_patterns = [
    path('list_question/', LibPageAPI.as_view({'get': 'retrieve'})),
    path('form/', LibPageAPI.as_view({'post': 'create'})),
    path('predict_answer/', LibPageAPI.as_view({'post': 'get_response'})),
]

# основной патерн включающие другие патерны страниц
urlpatterns = [
    path('widget_admin/', include(extra_admin_site_patterns)),
    path('api/lib/', include(extra_lib_patterns)),
]
