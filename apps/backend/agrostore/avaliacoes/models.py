from django.db import models
from django.db.models.functions import Length
from django.db.models.lookups import LessThanOrEqual
from django.core.validators import MinValueValidator, MaxValueValidator
from agrostore.main.models import BaseModel
from agrostore.usuarios.models import Usuario
from agrostore.produtos.models import Produto
from agrostore.pedidos.models import PedidoProduto


class Avaliacao(BaseModel):
    avaliacao_id = models.BigAutoField(primary_key=True, db_column='id_avaliacao')
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='avaliacoes', db_column='id_usuario')
    produto = models.ForeignKey(
        Produto, on_delete=models.SET_NULL, null=True, blank=True, related_name='avaliacoes', db_column='id_produto'
    )
    pedido_produto = models.OneToOneField(
        PedidoProduto, on_delete=models.PROTECT, related_name='avaliacao', db_column='id_pedido_produto'
    )
    nota = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True)

    class Meta:
        db_table = 'avaliacao'
        constraints = [
            models.CheckConstraint(condition=models.Q(nota__range=(1, 5)), name='avaliacao_nota_check'),
            models.CheckConstraint(
                condition=LessThanOrEqual(Length('comentario'), 500),
                name='ck_avaliacao_comentario_tamanho',
                violation_error_message='O comentário deve ter no máximo 500 caracteres.',
            ),
        ]

    def __str__(self):
        nome_produto = self.produto.nome if self.produto_id else self.pedido_produto.nome_produto
        return f"{self.usuario.nome} - {nome_produto} ({self.nota}★)"
