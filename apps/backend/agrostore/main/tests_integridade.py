from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from agrostore.avaliacoes.models import Avaliacao
from agrostore.favoritos.models import Favorito
from agrostore.lojas.models import Loja
from agrostore.pedidos.models import Pedido, PedidoProduto, StatusPedido
from agrostore.produtos.models import Categoria, Produto
from agrostore.usuarios.models import Genero, Usuario


class IntegridadeTests(TestCase):
    def setUp(self):
        genero = Genero.objects.get(id_genero='M')
        self.produtor = Usuario.objects.create_user(
            cpf='52345678902', email='produtor@example.com', password='SenhaForte123', nome='Produtor',
            data_nascimento=date(1990, 1, 1), genero=genero, is_produtor=True,
        )
        self.loja = Loja.objects.create(proprietario=self.produtor, nome='Loja Teste', cnpj='52345678000199')
        self.categoria = Categoria.objects.create(nome='Frutas')
        self.produto = Produto.objects.create(loja=self.loja, nome='Maca', estoque=10, categoria=self.categoria)

    def test_banco_recusa_estoque_negativo(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Produto.objects.create(loja=self.loja, nome='Pera', estoque=-1, categoria=self.categoria)

    def test_banco_recusa_nota_de_avaliacao_fora_de_1_a_5(self):
        status_pedido = StatusPedido.objects.create(status='Entregue')
        pedido = Pedido.objects.create(loja=self.loja, status=status_pedido)
        item = PedidoProduto.objects.create(
            pedido=pedido, produto=self.produto, nome_produto='Maca',
            quantidade=1, valor_unitario=Decimal('10.00'), subtotal=Decimal('10.00'),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Avaliacao.objects.create(usuario=self.produtor, produto=self.produto, pedido_produto=item, nota=6)

    def test_banco_recusa_favorito_duplicado(self):
        Favorito.objects.create(usuario=self.produtor, produto=self.produto)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favorito.objects.create(usuario=self.produtor, produto=self.produto)

    def test_produto_novo_recebe_sku_de_14_digitos(self):
        self.produto.refresh_from_db()
        self.assertEqual(len(self.produto.sku), 14)
        self.assertTrue(self.produto.sku.isdigit())
