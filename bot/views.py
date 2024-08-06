from rest_framework.response import Response
from rest_framework.views import APIView

from bot.chat_predict import LibChatPredict


chat_predict = LibChatPredict()


class ChatAPIView(APIView):
    def post(self, request):
        msg = request.data.get('msg', 'пока')
        print(msg)

        if msg.startswith(('меня зовут', 'привет, меня зовут')):
            name = msg.split()[-1]
            res = chat_predict.get_answer(msg).replace("{n}", name)
        else:
            res = chat_predict.get_answer(msg)

        return Response({'answer': res})
