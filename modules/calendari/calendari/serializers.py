from rest_framework import serializers
from .models import Esdeveniment, CalendariConfig


class CalendariConfigSerializer(serializers.ModelSerializer):
    esta_connectat = serializers.BooleanField(read_only=True)

    class Meta:
        model = CalendariConfig
        fields = (
            'id', 'ms_calendar_id', 'sincronitzar_licitacions',
            'sincronitzar_ofertes', 'dies_avis_previ', 'esta_connectat',
        )
        read_only_fields = ('ms_access_token', 'ms_refresh_token', 'ms_token_expiry')


class EsdevenimentSerializer(serializers.ModelSerializer):
    licitacio_titol = serializers.CharField(source='licitacio.titol', read_only=True, default='')
    creador_nom = serializers.CharField(source='creador.get_full_name', read_only=True)

    class Meta:
        model = Esdeveniment
        fields = (
            'id', 'licitacio', 'licitacio_titol', 'oferta', 'creador', 'creador_nom',
            'assistents', 'tipus', 'titol', 'descripcio', 'ubicacio',
            'inici', 'fi', 'tot_el_dia', 'recordatori_minuts',
            'estat', 'ms_event_id', 'creada_en',
        )
        read_only_fields = ('estat', 'ms_event_id', 'creada_en')

    def create(self, validated_data):
        validated_data['creador'] = self.context['request'].user
        return super().create(validated_data)
