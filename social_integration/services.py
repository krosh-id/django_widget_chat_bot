# listeners of social networks events
from django.core.cache import cache
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from social_integration.handlers import VkMethod

vk_session = vk_api.VkApi(token='vk1.a.4TQ9oQ9O4RAJOg-LVz9AkF_2MW4wqFT6psKbrsrfksn342Ct39az8jdMnlz8wei2B5zUoAxfK_YfKEKSiZUKQucVxGda1xC7l2Eis6SED1Tqw-4HzHdPizHxAxD6LZ3LLHSvlXYk64tEhob0NSQC42qvgZeE0CG1gEIRNj8xhceywlpWNP5jYS-AtNQVzp31M1C9y3vw0UuYl4-PmBb4Ng')
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

def start_vk_listeners():
    '''
        Подключение к VK API и постоянное ожидание событий
    '''
    print("Cлушатель событий VK запущен!")
    vk_methods = VkMethod(vk_session)
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.to_me:
                msg = event.text.lower().strip()
                id = event.user_id
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


