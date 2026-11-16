from rest_framework import serializers
from rest_framework.utils import html

from .imagens import MENSAGEM_IMAGEM_INVALIDA, nome_gerenciado, validar_imagem_enviada


class CampoImagemUnica(serializers.FileField):
    """Imagem única da loja ou do usuário: sai como URL absoluta, ou null sem imagem válida."""

    def __init__(self, pasta, **kwargs):
        self.pasta = pasta
        if 'required' not in kwargs:
            kwargs['required'] = False
        if not kwargs.get('read_only') and 'validators' not in kwargs:
            kwargs['validators'] = [validar_imagem_enviada]
        kwargs['error_messages'] = {
            'invalid': MENSAGEM_IMAGEM_INVALIDA,
            'required': MENSAGEM_IMAGEM_INVALIDA,
            'null': MENSAGEM_IMAGEM_INVALIDA,
            'empty': MENSAGEM_IMAGEM_INVALIDA,
            'no_name': MENSAGEM_IMAGEM_INVALIDA,
        }
        super().__init__(**kwargs)

    def get_value(self, dictionary):
        if html.is_html_input(dictionary) and dictionary.get(self.field_name) == '':
            return ''
        return super().get_value(dictionary)

    def to_representation(self, valor):
        if not valor or not nome_gerenciado(valor.name, self.pasta):
            return None
        url = valor.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url
