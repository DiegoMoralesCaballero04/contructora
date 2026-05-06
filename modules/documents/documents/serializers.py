from rest_framework import serializers
from .models import Document, VersioDocument, CategoriaDocument, AccesDocument, PermisDocument


class CategoriaDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaDocument
        fields = ('id', 'nom', 'codi', 'descripcio', 'retencio_anys', 'requereix_aprovacio', 'ordre')


class VersioDocumentSerializer(serializers.ModelSerializer):
    creada_per_nom = serializers.CharField(source='creada_per.get_full_name', read_only=True, default='')

    class Meta:
        model = VersioDocument
        fields = (
            'id', 'numero_versio', 's3_key', 'sha256', 'mida_bytes',
            'notes_versio', 'creada_per', 'creada_per_nom', 'creada_en',
        )
        read_only_fields = fields


class AccesDocumentSerializer(serializers.ModelSerializer):
    usuari_nom = serializers.CharField(source='usuari.get_full_name', read_only=True, default='')

    class Meta:
        model = AccesDocument
        fields = ('id', 'usuari', 'usuari_nom', 'accio', 'ip_address', 'timestamp', 'versio')
        read_only_fields = fields


class PermisDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermisDocument
        fields = ('id', 'usuari', 'rol', 'nivell', 'atorgat_per', 'atorgat_en', 'expira_en')


class DocumentSerializer(serializers.ModelSerializer):
    versio_actual = VersioDocumentSerializer(read_only=True)
    categoria_nom = serializers.CharField(source='categoria.nom', read_only=True)
    pujat_per_nom = serializers.CharField(source='pujat_per.get_full_name', read_only=True)
    mida_llegible = serializers.CharField(read_only=True)

    class Meta:
        model = Document
        fields = (
            'id', 'nom', 'descripcio', 'categoria', 'categoria_nom', 'tipus', 'estat',
            'nom_fitxer_original', 'mida_bytes', 'mida_llegible', 'mime_type',
            'sha256', 'metadades', 'etiquetes',
            'licitacio', 'oferta',
            'pujat_per', 'pujat_per_nom', 'propietari',
            'data_document', 'data_caducitat', 'data_eliminacio_prevista',
            'versio_actual', 'creada_en', 'actualitzada_en',
        )
        read_only_fields = (
            'sha256', 'mida_bytes', 'nom_fitxer_original', 'mime_type',
            'estat', 'pujat_per', 'creada_en', 'actualitzada_en',
        )
