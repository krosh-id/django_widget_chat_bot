from django.contrib import admin
from .models import ChatLog

@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('user_message', 'bot_response', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user_message', 'bot_response')
