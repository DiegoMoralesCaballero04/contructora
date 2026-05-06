from rest_framework import serializers
from .models import EmpresaProspect, CampanyaMarketing, PlantillaEmail, EnviamentEmail


class EmpresaProspectSerializer(serializers.ModelSerializer):
    pot_rebre_emails = serializers.BooleanField(read_only=True)
    taxa_obertura = serializers.SerializerMethodField()

    class Meta:
        model = EmpresaProspect
        fields = (
            'id', 'nom', 'sector', 'origen', 'estat', 'email_principal',
            'emails_alternatius', 'telefon', 'web', 'direccio', 'poblacio', 'provincia',
            'persona_contacte', 'carrec_contacte', 'scoring', 'notes',
            'consentiment_gdpr', 'data_consentiment', 'baixa_voluntaria', 'data_baixa',
            'pot_rebre_emails', 'taxa_obertura', 'assignat_a', 'creada_en',
        )
        read_only_fields = (
            'scoring', 'token_baixa', 'data_baixa', 'baixa_voluntaria',
            'creada_en', 'pot_rebre_emails',
        )

    def get_taxa_obertura(self, obj) -> float:
        total = obj.enviaments.filter(estat='ENVIAT').count()
        oberts = obj.enviaments.filter(obert=True).count()
        return round(oberts / total * 100, 1) if total else 0.0


class PlantillaEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantillaEmail
        fields = '__all__'
        read_only_fields = ('creada_en', 'actualitzada_en')


class CampanyaMarketingSerializer(serializers.ModelSerializer):
    taxa_obertura = serializers.FloatField(read_only=True)
    plantilla_nom = serializers.CharField(source='plantilla.nom', read_only=True)

    class Meta:
        model = CampanyaMarketing
        fields = (
            'id', 'nom', 'plantilla', 'plantilla_nom', 'estat', 'segments',
            'millorar_amb_ia', 'personalitzar_per_empresa', 'data_programada',
            'total_destinataris', 'total_enviats', 'total_errors',
            'total_obertures', 'total_clics', 'taxa_obertura',
            'creada_en', 'iniciada_en', 'completada_en',
        )
        read_only_fields = (
            'estat', 'total_destinataris', 'total_enviats', 'total_errors',
            'total_obertures', 'total_clics', 'creada_en', 'iniciada_en', 'completada_en',
        )


class EnviamentEmailSerializer(serializers.ModelSerializer):
    prospect_nom = serializers.CharField(source='prospect.nom', read_only=True)

    class Meta:
        model = EnviamentEmail
        fields = (
            'id', 'prospect', 'prospect_nom', 'assumpte_final', 'estat',
            'obert', 'obert_en', 'clicat', 'clicat_en', 'enviat_en', 'error_msg',
        )
        read_only_fields = fields
