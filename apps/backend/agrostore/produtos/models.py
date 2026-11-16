import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.utils import timezone

from agrostore.main.imagens import EXTENSOES_IMAGEM, nome_arquivo_aleatorio
from agrostore.main.models import BaseModel
from agrostore.lojas.models import Loja


def caminho_imagem_produto(produto, nome_arquivo):
    return nome_arquivo_aleatorio('produtos', nome_arquivo)


class Categoria(BaseModel):
    categoria_id = models.BigAutoField(primary_key=True, db_column='id_categoria')
    nome = models.CharField(max_length=100, unique=True)
    ativo = models.BooleanField(default=True, db_column='esta_ativa')

    class Meta:
        db_table = 'categoria'

    def __str__(self):
        return self.nome


class Produto(BaseModel):
    LIMITE_ESTOQUE_BAIXO = 5

    produto_id = models.BigAutoField(primary_key=True, default=None, db_column='id_produto')
    loja = models.ForeignKey(Loja, on_delete=models.PROTECT, related_name='produtos', db_column='id_loja')
    nome = models.CharField(max_length=155)
    descricao = models.TextField(blank=True)
    estoque = models.IntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True, blank=True)
    ativo = models.BooleanField(default=True, db_column='esta_ativo')
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, db_column='id_categoria')

    class Meta:
        db_table = 'produto'
        constraints = [
            models.CheckConstraint(condition=models.Q(estoque__gte=0), name='produto_estoque_check'),
        ]

    def __str__(self):
        return self.nome

    @property
    def estoque_baixo(self):
        return 0 < self.estoque <= self.LIMITE_ESTOQUE_BAIXO

    @property
    def disponivel_para_compra(self):
        return self.ativo and self.loja.ativa and self.estoque > 0

    def gerar_sku(self):
        if self.loja_id is None or self.loja_id > 9999:
            raise ValueError('Identificador de loja excede o limite de 4 dígitos para o SKU.')
        if self.categoria_id is None or self.categoria_id > 9999:
            raise ValueError('Identificador de categoria excede o limite de 4 dígitos para o SKU.')
        if self.produto_id is None or self.produto_id > 999999:
            raise ValueError('Identificador de produto excede o limite de 6 dígitos para o SKU.')

        return str(self.loja_id).zfill(4) + str(self.categoria_id).zfill(4) + str(self.produto_id).zfill(6)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            return super().save(*args, **kwargs)

        self.sku = f'pendente-{uuid.uuid4().hex}'
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.sku = self.gerar_sku()
            super().save(update_fields=['sku'])


class ImagemProduto(BaseModel):
    LIMITE_POR_PRODUTO = 5

    id = models.BigAutoField(primary_key=True, db_column='id_imagem')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='imagens', db_column='id_produto')
    imagem = models.FileField(
        upload_to=caminho_imagem_produto,
        max_length=255,
        validators=[FileExtensionValidator(EXTENSOES_IMAGEM)],
        db_column='caminho',
    )
    ordem = models.PositiveIntegerField(default=0)
    e_principal = models.BooleanField(default=False)

    class Meta:
        db_table = 'imagem'
        ordering = ['ordem', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['produto'],
                condition=models.Q(e_principal=True),
                name='imagem_principal_unica_por_produto',
            ),
            models.UniqueConstraint(fields=['produto', 'ordem'], name='uq_imagem_produto_ordem'),
        ]

    def __str__(self):
        return f'{self.produto.nome} - imagem {self.ordem + 1}'

    def definir_como_principal(self):
        with transaction.atomic():
            ImagemProduto.objects.filter(produto_id=self.produto_id, e_principal=True).exclude(pk=self.pk).update(e_principal=False)
            self.e_principal = True
            self.save(update_fields=['e_principal', 'data_atualizacao'])

    def excluir(self):
        nome_arquivo = self.imagem.name
        storage = self.imagem.storage
        with transaction.atomic():
            era_principal = self.e_principal
            self.delete()
            if era_principal:
                proxima = ImagemProduto.objects.filter(produto_id=self.produto_id).first()
                if proxima:
                    proxima.definir_como_principal()
        storage.delete(nome_arquivo)


class PrecoProduto(BaseModel):
    id = models.BigAutoField(primary_key=True, db_column='id_preco_produto')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='precos', db_column='id_produto')
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, db_column='valor_venda')
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, db_column='valor_custo')
    porcentagem_desconto = models.IntegerField(null=True, blank=True)
    vigencia_inicio = models.DateTimeField(default=timezone.now)
    vigencia_fim = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'preco_produto'
        constraints = [
            models.CheckConstraint(condition=models.Q(preco_venda__gte=0), name='preco_produto_valor_venda_check'),
            models.CheckConstraint(condition=models.Q(preco_custo__gte=0), name='preco_produto_valor_custo_check'),
            models.CheckConstraint(
                condition=models.Q(porcentagem_desconto__range=(0, 100)),
                name='preco_produto_porcentagem_desconto_check',
            ),
            models.CheckConstraint(
                condition=models.Q(vigencia_fim__isnull=True) | models.Q(vigencia_fim__gte=models.F('vigencia_inicio')),
                name='ck_preco_vigencia',
            ),
        ]

    @property
    def valor_desconto(self):
        porcentagem = Decimal(self.porcentagem_desconto or 0)
        return (self.preco_venda * porcentagem / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def preco_final(self):
        return self.preco_venda - self.valor_desconto

    def save(self, *args, **kwargs):
        if self.porcentagem_desconto is None:
            self.porcentagem_desconto = 0
        if not 0 <= self.porcentagem_desconto <= 100:
            raise ValueError('Porcentagem de desconto deve estar entre 0 e 100')
        with transaction.atomic():
            if not self.pk:
                PrecoProduto.objects.filter(produto=self.produto, vigencia_fim__isnull=True).update(vigencia_fim=timezone.now())
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.produto.nome} - R$ {self.preco_venda}"
