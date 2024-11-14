from rest_framework import serializers

from bot.models import Page, Category, Question, FormQuestion, QuestionTopicNotification


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'answer']


class QuestionTopicNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionTopicNotification
        fields = ['id', 'topic']


class CategorySerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'questions']


class FormQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormQuestion
        fields = "__all__"


