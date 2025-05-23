from django.db import models


class ChatLog(models.Model):
    user_message = models.TextField(verbose_name="Сообщение пользователя")
    bot_response = models.TextField(verbose_name="Ответа бота")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата сообщения")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Лог чата"
        verbose_name_plural = "Логи чата"

    def __str__(self):
        return f"[{self.created_at}] User: {self.user_message[:30]} | Bot: {self.bot_response[:30]}"
