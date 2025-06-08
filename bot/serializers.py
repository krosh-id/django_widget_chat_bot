# import bleach
from rest_framework import serializers
from bot.models import Page, Category, Question, FormQuestion, QuestionTopicNotification, Institution


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'answer']

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     representation['answer'] = bleach.clean(representation['answer'])
    #     return representation


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
    topic = serializers.CharField(write_only=True)

    class Meta:
        model = FormQuestion
        fields = [
            'id',
            'full_name',
            'mobile_phone',
            'email',
            'date_created',
            'text',
            'page',
            'topic_question',
            'topic',  # write-only field for topic name
            'institution',
        ]
        extra_kwargs = {
            'topic_question': {'read_only': True},
        }

    def create(self, validated_data):
        # Remove the topic from validated_data as it's not a direct model field
        topic_name = validated_data.pop('topic', None)

        if not topic_name:
            raise serializers.ValidationError({"topic": "This field is required."})

        # Find the corresponding QuestionTopicNotification
        try:
            topic = QuestionTopicNotification.objects.filter(topic=topic_name).all()
        except QuestionTopicNotification.DoesNotExist:
            raise serializers.ValidationError({"topic": "Topic does not exist"})

        if len(topic) > 1:
            try:
                topic = topic.get(institution=validated_data['institution'])
            except QuestionTopicNotification.DoesNotExist:
                topic = topic.get(institution=None)
        else:
            topic = topic.get(institution=None)
        # Set the topic_question relationship
        validated_data['topic_question'] = topic
        # Proceed with normal creation
        return super().create(validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Add the topic name to the representation
        representation['topic'] = instance.topic_question.topic
        return representation

class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = "__all__"


