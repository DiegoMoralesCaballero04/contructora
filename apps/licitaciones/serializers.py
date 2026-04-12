from rest_framework import serializers
from .models import Licitacion, Organismo, CriterioAdjudicacion


class CriterioSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterioAdjudicacion
        fields = ('nombre', 'puntuacion_maxima', 'formula', 'es_economico', 'orden')


class OrganismoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organismo
        fields = ('id', 'nombre', 'provincia', 'municipio')


class LicitacionListSerializer(serializers.ModelSerializer):
    organismo_nombre = serializers.CharField(source='organismo.nombre', read_only=True)
    dias_restantes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Licitacion
        fields = (
            'id', 'expediente_id', 'titulo', 'organismo_nombre', 'provincia',
            'importe_base', 'fecha_limite_oferta', 'dias_restantes',
            'estado', 'pdf_descargado',
        )


class LicitacionDetailSerializer(serializers.ModelSerializer):
    organismo = OrganismoSerializer(read_only=True)
    criterios = CriterioSerializer(many=True, read_only=True)
    dias_restantes = serializers.IntegerField(read_only=True)
    tiene_extraccion = serializers.BooleanField(read_only=True)

    class Meta:
        model = Licitacion
        fields = '__all__'
