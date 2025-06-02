from decouple import config
from django.core.cache import cache
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from social_integration.handlers import VkMethod

vk_session = vk_api.VkApi(token=config('VK_TOKEN'))
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)
limit_message = 50 # лимит сообщения пользователя за 5 минут

# listeners of social networks events
def start_vk_listeners():
    """
        Подключение к VK API и постоянное ожидание событий
    """
    print("Cлушатель событий VK запущен!")
    vk_methods = VkMethod(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                msg = event.text.lower().strip()
                id = event.user_id
                requests = cache.get(f'user_request_{id}')
                if requests and requests >= limit_message:
                   vk_methods.send_msg(id, 'От вас поступило слишком много сообщений( \n Попробуйте написать позже.')
                   break
                elif requests and requests < limit_message:
                    requests += 1
                    cache.set(f'user_request_{id}', requests, timeout=300)
                else:
                    requests = 1
                    cache.set(f'user_request_{id}', requests, timeout=300)

                if cache.get(f'user_step_{id}'):
                    vk_methods.send_form(id, msg)
                else:
                    match msg:
                        case 'начать':
                            vk_methods.send_main_menu(id)
                        case 'главное меню':
                            vk_methods.send_main_menu(id)
                        case 'задать другой вопрос':
                            vk_methods.send_msg_keyboard(id, vk_methods.keyboard_PREFORM,
                                                         'Ты можешь задать любой вопрос сотруднику, заполнив быструю анкету')
                        case 'продолжить':
                            vk_methods.send_form(id, msg)
                        case 'отмена':
                            vk_methods.send_main_menu(id)
                        case _:
                            try:
                                number_question = int(msg)
                                vk_methods.send_answer(id, number_question)
                            except ValueError:
                                vk_methods.send_msg_keyboard(id, vk_methods.keyboard_MENU,
                                                             'Извини, я тебя не понимаю :( \nИспользуй цифры или кнопки. '
                                                             'Ты также можешь задать другой вопрос с помощью кнопки на клавиатуре')


