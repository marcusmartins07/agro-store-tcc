from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from agrostore.lojas.models import Loja
from agrostore.pedidos.models import Pedido, PedidoCliente, PedidoProduto, StatusPedido
from agrostore.produtos.models import Categoria, Produto
from agrostore.usuarios.models import Genero, Usuario
from .models import Avaliacao


def criar_usuario(cpf, email, is_produtor=False):
    return Usuario.objects.create_user(
        cpf=cpf, email=email, password='senha123', nome=email.split('@')[0],
        data_nascimento=date(1990, 1, 1), genero=Genero.objects.get(id_genero='M'), is_produtor=is_produtor,
    )


def criar_pedido(cliente, loja, produto, status_nome):
    status_pedido = StatusPedido.objects.get_or_create(status=status_nome)[0]
    pedido = Pedido.objects.create(loja=loja, status=status_pedido)
    PedidoCliente.objects.create(
        pedido=pedido, usuario=cliente, nome=cliente.nome, cpf=cliente.cpf, email=cliente.email,
        data_nascimento=cliente.data_nascimento, genero='Masculino',
    )
    return PedidoProduto.objects.create(
        pedido=pedido, produto=produto, nome_produto=produto.nome, quantidade=1,
        valor_unitario=Decimal('10.00'), subtotal=Decimal('10.00'),
    )


class AvaliacoesTests(APITestCase):
    def setUp(self):
        produtor = criar_usuario('12345678901', 'produtor@example.com', is_produtor=True)
        self.cliente = criar_usuario('12345678903', 'cliente@example.com')
        self.outro_cliente = criar_usuario('12345678904', 'outro-cliente@example.com')
        loja = Loja.objects.create(proprietario=produtor, nome='Feira Verde', cnpj='12345678000199')
        categoria = Categoria.objects.create(nome='Frutas')
        self.produto = Produto.objects.create(loja=loja, nome='Maca', estoque=10, categoria=categoria)
        self.outro_produto = Produto.objects.create(loja=loja, nome='Pera', estoque=10, categoria=categoria)
        self.item_entregue = criar_pedido(self.cliente, loja, self.produto, 'Entregue')
        self.item_pendente = criar_pedido(self.cliente, loja, self.produto, 'Pendente')
        self.item_outro_cliente = criar_pedido(self.outro_cliente, loja, self.produto, 'Entregue')
        self.item_outro_produto = criar_pedido(self.cliente, loja, self.outro_produto, 'Entregue')
        self.client.force_authenticate(self.cliente)

    def enviar(self, item, nota=5):
        return self.client.post('/api/v1/avaliacoes/', {'pedido_produto': item.pedido_produto_id, 'nota': nota}, format='json')

    def test_titular_avalia_item_de_pedido_entregue(self):
        response = self.enviar(self.item_entregue)
        self.assertEqual(response.status_code, 201)
        avaliacao = Avaliacao.objects.get()
        self.assertEqual(avaliacao.usuario, self.cliente)
        self.assertEqual(avaliacao.produto, self.produto)

    def test_item_de_pedido_de_outro_cliente_e_bloqueado(self):
        response = self.enviar(self.item_outro_cliente)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['pedido_produto'], ['Este item não pertence ao seu pedido.'])

    def test_pedido_pendente_nao_pode_ser_avaliado(self):
        response = self.enviar(self.item_pendente)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['pedido_produto'], ['Só é possível avaliar pedidos entregues.'])

    def test_item_ja_avaliado_e_recusado(self):
        self.enviar(self.item_entregue)
        response = self.enviar(self.item_entregue)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['pedido_produto'], ['Este item já foi avaliado.'])

    def test_nota_6_e_recusada(self):
        response = self.enviar(self.item_entregue, nota=6)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Avaliacao.objects.exists())

    def test_envio_sem_autenticacao_e_recusado(self):
        self.client.force_authenticate(user=None)
        response = self.enviar(self.item_entregue)
        self.assertEqual(response.status_code, 401)

    def test_listagem_publica_filtra_por_produto(self):
        Avaliacao.objects.create(usuario=self.cliente, produto=self.produto, pedido_produto=self.item_entregue, nota=5)
        Avaliacao.objects.create(usuario=self.cliente, produto=self.outro_produto, pedido_produto=self.item_outro_produto, nota=4)
        self.client.force_authenticate(user=None)
        response = self.client.get(f'/api/v1/avaliacoes/?produto={self.produto.produto_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['produto'], self.produto.produto_id)

    def test_put_patch_e_delete_pela_api_sao_recusados(self):
        avaliacao = Avaliacao.objects.create(usuario=self.cliente, produto=self.produto, pedido_produto=self.item_entregue, nota=5)
        url = f'/api/v1/avaliacoes/{avaliacao.avaliacao_id}/'
        self.assertEqual(self.client.put(url, {'nota': 1}, format='json').status_code, 405)
        self.assertEqual(self.client.patch(url, {'nota': 1}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
