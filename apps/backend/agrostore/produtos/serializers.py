from rest_framework import serializers

from agrostore.main.imagens import TAMANHO_MAXIMO_IMAGEM as TAMANHO_MAXIMO_IMAGEM_PRODUTO
from agrostore.main.imagens import MENSAGEM_IMAGEM_GRANDE, MENSAGEM_IMAGEM_INVALIDA, arquivo_e_imagem
from .models import Produto, PrecoProduto, Categoria, ImagemProduto


def url_imagem_principal(produto, request):
    principal = None
    for imagem in produto.imagens.all():
        if imagem.e_principal:
            principal = imagem
            break
    if principal is None:
        return None
    url = principal.imagem.url
    return request.build_absolute_uri(url) if request else url


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = (
            'categoria_id',
            'nome',
            'ativo'
        )


class PrecoProdutoSerializer(serializers.ModelSerializer):
    porcentagem_desconto = serializers.IntegerField(
        required=False, allow_null=True, error_messages={'invalid': 'Informe um desconto entre 0 e 100%.'}
    )
    valor_desconto = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    preco_final = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    vigencia_inicio = serializers.DateTimeField(read_only=True)
    vigencia_fim = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PrecoProduto
        fields = [
            'id',
            'produto',
            'preco_venda',
            'preco_custo',
            'porcentagem_desconto',
            'valor_desconto',
            'preco_final',
            'vigencia_inicio',
            'vigencia_fim',
        ]

    def validate_preco_venda(self, valor):
        if valor < 0:
            raise serializers.ValidationError('O preço de venda não pode ser negativo.')
        return valor

    def validate_preco_custo(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError('O preço de custo não pode ser negativo.')
        return valor

    def validate_porcentagem_desconto(self, valor):
        if valor is not None and not 0 <= valor <= 100:
            raise serializers.ValidationError('Informe um desconto entre 0 e 100%.')
        return valor

    def validate(self, attrs):
        if attrs.get('porcentagem_desconto') is None:
            attrs['porcentagem_desconto'] = 0
        return attrs


class ImagemProdutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagemProduto
        fields = ['id', 'imagem', 'ordem', 'e_principal']
        read_only_fields = ['ordem']

    def validate_imagem(self, imagem):
        if self.instance is not None:
            raise serializers.ValidationError('Para trocar a imagem, exclua esta e envie uma nova.')
        if imagem.size > TAMANHO_MAXIMO_IMAGEM_PRODUTO:
            raise serializers.ValidationError(MENSAGEM_IMAGEM_GRANDE)
        if not arquivo_e_imagem(imagem):
            raise serializers.ValidationError(MENSAGEM_IMAGEM_INVALIDA)
        return imagem

    def validate_e_principal(self, e_principal):
        if self.instance is not None and self.instance.e_principal and not e_principal:
            raise serializers.ValidationError('Defina outra imagem como principal para desmarcar esta.')
        return e_principal


class ProdutoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.StringRelatedField(source='categoria', read_only=True)
    loja_nome = serializers.StringRelatedField(source='loja', read_only=True)
    preco = serializers.SerializerMethodField()
    preco_original = serializers.SerializerMethodField()
    desconto = serializers.SerializerMethodField()
    preco_venda = serializers.SerializerMethodField()
    porcentagem_desconto = serializers.SerializerMethodField()
    preco_custo = serializers.SerializerMethodField()
    imagem = serializers.SerializerMethodField()
    imagens = ImagemProdutoSerializer(many=True, read_only=True)
    estoque_baixo = serializers.ReadOnlyField()

    class Meta:
        model = Produto
        fields = [
            'produto_id',
            'loja',           # escrita
            'loja_nome',      # leitura
            'nome',
            'descricao',
            'categoria',      # escrita
            'categoria_nome',  # leitura
            'estoque',
            'estoque_baixo',  # leitura: estoque de 1 a Produto.LIMITE_ESTOQUE_BAIXO
            'sku',
            'ativo',
            'preco',
            'preco_original',
            'desconto',
            'preco_venda',
            'porcentagem_desconto',
            'preco_custo',
            'imagem',        # leitura: URL da imagem principal
            'imagens',        # leitura: gerenciadas em /produtos/{id}/imagens/
        ]
        read_only_fields = ['loja', 'sku']

    def get_imagem(self, obj):
        return url_imagem_principal(obj, self.context.get('request'))

    def validate_estoque(self, estoque):
        if estoque < 0:
            raise serializers.ValidationError('O estoque não pode ser negativo.')
        return estoque

    def validate(self, attrs):
        categoria = attrs.get('categoria')
        if categoria is not None and not categoria.ativo:
            raise serializers.ValidationError({
                'categoria': 'A categoria selecionada está inativa e não pode ser usada em novos cadastros ou alterações.'
            })
        return attrs

    def to_representation(self, instance):
        dados = super().to_representation(instance)
        if not self._pode_ver_custo(instance):
            dados.pop('preco_custo', None)
        return dados

    def _pode_ver_custo(self, produto):
        usuario = getattr(self.context.get('request'), 'user', None)
        if usuario is None or not usuario.is_authenticated:
            return False
        return usuario.is_staff or produto.loja.proprietario_id == usuario.pk

    def get_preco_atual(self, obj):
        preco_atual = None
        for preco in obj.precos.all():
            if preco.vigencia_fim is None:
                if preco_atual is None or preco.pk > preco_atual.pk:
                    preco_atual = preco
        return preco_atual

    def get_preco(self, obj):
        preco = self.get_preco_atual(obj)
        return preco.preco_final if preco else None

    def get_preco_venda(self, obj):
        preco = self.get_preco_atual(obj)
        return preco.preco_venda if preco else None

    def get_porcentagem_desconto(self, obj):
        preco = self.get_preco_atual(obj)
        return (preco.porcentagem_desconto or 0) if preco else None

    def get_preco_custo(self, obj):
        preco = self.get_preco_atual(obj)
        return preco.preco_custo if preco else None

    def get_preco_original(self, obj):
        preco = self.get_preco_atual(obj)
        if preco:
            return preco.preco_venda
        return None

    def get_desconto(self, obj):
        preco = self.get_preco_atual(obj)
        if preco:
            return preco.porcentagem_desconto
        return None
