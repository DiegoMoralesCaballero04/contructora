from rest_framework import serializers

from .models import Empresa


class EmpresaSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = (
            'id', 'nombre_empresa', 'direccion', 'ciudad', 'pais',
            'email_contacto', 'telefono', 'logo', 'logo_url',
            'descripcion', 'actualizado_en',
        )
        read_only_fields = ('id', 'actualizado_en', 'logo_url')
        extra_kwargs = {
            'logo': {'write_only': True, 'required': False},
        }

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None
