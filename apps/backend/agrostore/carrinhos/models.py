from decimal import Decimal

from django.db import models

from agrostore.lojas.models import Loja
from agrostore.main.models import BaseModel
from agrostore.produtos.models import Produto
from agrostore.usuarios.models import Usuario


class Carrinho(BaseModel):
    carrinho_id = models.BigAutoField(primary_key=True, db_column='id_carrinho')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='carrinhos', db_column='id_usuario')
    loja = models.ForeignKey(Loja, on_delete=models.CASCADE, db_column='id_loja')
    valor_bruto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_liquido = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'carrinho'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'loja'], name='uq_carrinho_usuario_loja'),
            models.CheckConstraint(condition=models.Q(valor_bruto__gte=0), name='carrinho_valor_bruto_check'),
            models.CheckConstraint(condition=models.Q(valor_desconto__gte=0), name='carrinho_valor_desconto_check'),
            models.CheckConstraint(condition=models.Q(valor_liquido__gte=0), name='carrinho_valor_liquido_check'),
        ]

    def __str__(self):
        return f"{self.usuario.nome} - {self.loja.nome}"

    def recalcular_totais(self):
        valor_bruto = Decimal('0.00')
        valor_desconto = Decimal('0.00')

        for item in self.itens.select_related('produto'):
            preco = item.preco_atual
            if not preco:
                continue

            valor_bruto += preco.preco_venda * item.quantidade
            valor_desconto += preco.valor_desconto * item.quantidade

        self.valor_bruto = valor_bruto
        self.valor_desconto = valor_desconto
        self.valor_liquido = valor_bruto - valor_desconto
        self.save(update_fields=['valor_bruto', 'valor_desconto', 'valor_liquido', 'data_atualizacao'])


class CarrinhoProduto(BaseModel):
    carrinho_produto_id = models.BigAutoField(primary_key=True, db_column='id_carrinho_produto')
    carrinho = models.ForeignKey(Carrinho, on_delete=models.CASCADE, related_name='itens', db_column='id_carrinho')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='itens_carrinho', db_column='id_produto')
    quantidade = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'carrinho_produto'
        constraints = [
            models.UniqueConstraint(fields=['carrinho', 'produto'], name='uq_carrinho_produto'),
        ]

    def __str__(self):
        return f"{self.produto.nome} x{self.quantidade}"

    @property
    def preco_atual(self):
        return self.produto.precos.filter(vigencia_fim__isnull=True).last()

    @property
    def valor_unitario(self):
        preco = self.preco_atual
        return preco.preco_venda if preco else None

    @property
    def valor_desconto(self):
        preco = self.preco_atual
        return preco.valor_desconto if preco else Decimal('0.00')

    @property
    def subtotal(self):
        preco = self.preco_atual
        return preco.preco_final * self.quantidade if preco else Decimal('0.00')
