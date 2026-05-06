from rest_framework import serializers
from .models import (
    Oferta, VersioOferta, Pressupost, LiniaPressupost,
    SolicitudSubcontractista, PlaSeguretat,
)


class LiniaPressupostSerializer(serializers.ModelSerializer):
    cost_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = LiniaPressupost
        fields = (
            'id', 'tipus', 'descripcio', 'unitat', 'quantitat',
            'cost_unitari', 'cost_total', 'subcontractista', 'ordre', 'notes',
        )


class PressupostSerializer(serializers.ModelSerializer):
    linies = LiniaPressupostSerializer(many=True, read_only=True)

    class Meta:
        model = Pressupost
        fields = ('id', 'titol', 'versio', 'actiu', 'cost_total', 'notes', 'linies', 'creada_en')
        read_only_fields = ('cost_total', 'creada_en')


class PlaSeguretatSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaSeguretat
        fields = (
            'id', 'partides_obra', 'contingut_ia', 'contingut_revisat',
            'prompt_versio', 'model_usat', 'validat', 'validat_en', 'pdf_s3_key',
        )
        read_only_fields = ('contingut_ia', 'prompt_versio', 'model_usat', 'validat_en', 'pdf_s3_key')


class SolicitudSubcontractistaSerializer(serializers.ModelSerializer):
    contacte_nom = serializers.CharField(source='contacte.nom', read_only=True)
    contacte_email = serializers.CharField(source='contacte.email', read_only=True)

    class Meta:
        model = SolicitudSubcontractista
        fields = (
            'id', 'contacte', 'contacte_nom', 'contacte_email', 'partides',
            'estat', 'preu_resposta', 'notes_resposta', 'enviada_en', 'resposta_en',
        )
        read_only_fields = ('estat', 'enviada_en', 'resposta_en', 'token_resposta')


class OfertaListSerializer(serializers.ModelSerializer):
    licitacio_titol = serializers.CharField(source='licitacio.titol', read_only=True)
    licitacio_expedient = serializers.CharField(source='licitacio.expediente_id', read_only=True)
    licitacio_limit = serializers.DateTimeField(source='licitacio.fecha_limite_oferta', read_only=True)
    pressupost_cost_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Oferta
        fields = (
            'id', 'licitacio', 'licitacio_titol', 'licitacio_expedient', 'licitacio_limit',
            'estat', 'preu_oferta', 'preu_optim_calculat', 'puntuacio_total',
            'nivell_risc', 'pressupost_cost_total', 'responsable', 'creada_en',
        )


class OfertaDetailSerializer(serializers.ModelSerializer):
    pressupostos = PressupostSerializer(many=True, read_only=True)
    pla_seguretat = PlaSeguretatSerializer(read_only=True)
    solicituds_subcontractista = SolicitudSubcontractistaSerializer(many=True, read_only=True)
    pressupost_cost_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    marge_estimat = serializers.FloatField(read_only=True)

    class Meta:
        model = Oferta
        fields = '__all__'
        read_only_fields = (
            'licitacio', 'preu_optim_calculat', 'puntuacio_economica',
            'nivell_risc', 'factors_risc', 'creada_en', 'actualitzada_en',
        )


class TransicioEstatSerializer(serializers.Serializer):
    estat = serializers.ChoiceField(choices=Oferta.Estat.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
