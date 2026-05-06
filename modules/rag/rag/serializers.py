from rest_framework import serializers
from .models import ConsultaRAG


class ConsultaRAGSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultaRAG
        fields = [
            'id', 'pregunta', 'filtres', 'context_recuperat',
            'resposta', 'fonts_citades', 'model_usat', 'temps_ms',
            'estat', 'error_msg', 'valoracio', 'comentari_valoracio',
            'creada_en',
        ]
        read_only_fields = [
            'id', 'context_recuperat', 'resposta', 'fonts_citades',
            'model_usat', 'temps_ms', 'estat', 'error_msg', 'creada_en',
        ]


class ConsultaRAGInputSerializer(serializers.Serializer):
    pregunta = serializers.CharField(max_length=2000)
    filtres = serializers.DictField(required=False, default=dict)
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)
    similitud_minima = serializers.FloatField(required=False, default=0.30, min_value=0.0, max_value=1.0)


class ValoracioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultaRAG
        fields = ['valoracio', 'comentari_valoracio']

    def validate_valoracio(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError('La valoració ha de ser entre 1 i 5.')
        return value
