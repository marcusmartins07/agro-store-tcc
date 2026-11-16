from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from agrostore.carrinhos.models import Carrinho, CarrinhoProduto
from agrostore.lojas.models import Loja
from agrostore.produtos.models import Categoria, PrecoProduto, Produto
from agrostore.usuarios.models import Genero, Telefone, TipoTelefone, Usuario
from .models import Pedido, PedidoCliente, PedidoProduto, StatusPedido


def criar_usuario(cpf, email, is_produtor=False):
    return Usuario.objects.create_user(
        cpf=cpf, email=email, password='senha123', nome=email.split('@')[0],
        data_nascimento=date(1990, 1, 1), genero=Genero.objects.get(id_genero='M'), is_produtor=is_produtor,
    )


def criar_status(nome):
    return StatusPedido.objects.get_or_create(status=nome)[0]


def criar_pedido(cliente, loja, produto, status_nome, quantidade=2):
    pedido = Pedido.objects.create(loja=loja, status=criar_status(status_nome))
    PedidoCliente.objects.create(
        pedido=pedido, usuario=cliente, nome=cliente.nome, cpf=cliente.cpf, email=cliente.email,
        data_nascimento=cliente.data_nascimento, genero='Masculino',
    )
    PedidoProduto.objects.create(
        pedido=pedido, produto=produto, nome_produto=produto.nome, quantidade=quantidade,
        valor_unitario=Decimal('10.00'), subtotal=Decimal('20.00'),
    )
    return pedido


class PedidosTests(APITestCase):
    def setUp(self):
        self.produtor = criar_usuario('12345678901', 'produtor@example.com', is_produtor=True)
        self.outro_produtor = criar_usuario('12345678902', 'outro-produtor@example.com', is_produtor=True)
        self.cliente = criar_usuario('12345678903', 'cliente@example.com')
        self.outro_cliente = criar_usuario('12345678904', 'outro-cliente@example.com')
        self.loja = Loja.objects.create(proprietario=self.produtor, nome='Feira Verde', cnpj='12345678000199')
        self.outra_loja = Loja.objects.create(proprietario=self.outro_produtor, nome='Sitio Outro', cnpj='12345678000288')
        categoria = Categoria.objects.create(nome='Frutas')
        self.produto = Produto.objects.create(loja=self.loja, nome='Maca', estoque=10, categoria=categoria)
        self.produto_outra_loja = Produto.objects.create(loja=self.outra_loja, nome='Pera', estoque=10, categoria=categoria)
        PrecoProduto.objects.create(produto=self.produto, preco_venda=Decimal('10.00'), porcentagem_desconto=10)
        PrecoProduto.objects.create(produto=self.produto_outra_loja, preco_venda=Decimal('5.00'))

    def criar_item(self, usuario, produto, quantidade=2):
        carrinho, _ = Carrinho.objects.get_or_create(usuario=usuario, loja=produto.loja)
        return CarrinhoProduto.objects.create(carrinho=carrinho, produto=produto, quantidade=quantidade)

    def finalizar(self, *itens):
        ids = [item.carrinho_produto_id for item in itens]
        return self.client.post('/api/v1/pedidos/', {'carrinho_produto_ids': ids}, format='json')

    def test_checkout_cria_um_pedido_por_loja(self):
        self.client.force_authenticate(self.cliente)
        item_a = self.criar_item(self.cliente, self.produto)
        item_b = self.criar_item(self.cliente, self.produto_outra_loja)
        response = self.finalizar(item_a, item_b)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(Pedido.objects.count(), 2)
        self.assertFalse(CarrinhoProduto.objects.filter(pk=item_a.pk).exists())
        self.assertFalse(CarrinhoProduto.objects.filter(pk=item_b.pk).exists())

    def test_checkout_baixa_o_estoque(self):
        self.client.force_authenticate(self.cliente)
        response = self.finalizar(self.criar_item(self.cliente, self.produto, quantidade=3))
        self.assertEqual(response.status_code, 201)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 7)

    def test_checkout_recusa_usuario_sem_autenticacao(self):
        item = self.criar_item(self.cliente, self.produto)
        response = self.finalizar(item)
        self.assertEqual(response.status_code, 401)

    def test_checkout_recusa_estoque_insuficiente(self):
        self.client.force_authenticate(self.cliente)
        item = self.criar_item(self.cliente, self.produto, quantidade=11)
        response = self.finalizar(item)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Pedido.objects.exists())

    def test_checkout_recusa_produto_inativo(self):
        self.client.force_authenticate(self.cliente)
        item = self.criar_item(self.cliente, self.produto)
        Produto.objects.filter(pk=self.produto.pk).update(ativo=False)
        response = self.finalizar(item)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Pedido.objects.exists())

    def test_checkout_recusa_item_de_outro_usuario(self):
        self.client.force_authenticate(self.cliente)
        item = self.criar_item(self.outro_cliente, self.produto)
        response = self.finalizar(item)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Um ou mais itens do carrinho são inválidos.')

    def test_checkout_recusa_item_com_quantidade_zero(self):
        self.client.force_authenticate(self.cliente)
        item = self.criar_item(self.cliente, self.produto, quantidade=0)
        response = self.finalizar(item)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Pedido.objects.exists())

    def test_checkout_ajusta_o_carrinho_de_outro_cliente_ao_novo_estoque(self):
        self.client.force_authenticate(self.cliente)
        item_cliente = self.criar_item(self.cliente, self.produto, quantidade=6)
        item_outro = self.criar_item(self.outro_cliente, self.produto, quantidade=8)
        response = self.finalizar(item_cliente)
        self.assertEqual(response.status_code, 201)
        item_outro.refresh_from_db()
        self.assertEqual(item_outro.quantidade, 4)

    def test_editar_o_perfil_do_cliente_nao_muda_o_nome_gravado_no_pedido(self):
        self.client.force_authenticate(self.cliente)
        self.finalizar(self.criar_item(self.cliente, self.produto))
        response = self.client.patch('/api/v1/usuarios/eu/', {'nome': 'Nome Novo'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nome'], 'Nome Novo')
        self.assertEqual(PedidoCliente.objects.get().nome, 'cliente')

    def test_mudar_o_preco_depois_nao_altera_o_pedido_feito(self):
        self.client.force_authenticate(self.cliente)
        self.finalizar(self.criar_item(self.cliente, self.produto))
        PrecoProduto.objects.create(produto=self.produto, preco_venda=Decimal('50.00'))
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.valor_liquido, Decimal('18.00'))
        self.assertEqual(pedido.itens.get().valor_unitario, Decimal('10.00'))

    def test_excluir_o_produto_preserva_o_item_do_pedido(self):
        pedido = criar_pedido(self.cliente, self.outra_loja, self.produto_outra_loja, 'Pendente')
        PrecoProduto.objects.filter(produto=self.produto_outra_loja).delete()
        self.produto_outra_loja.delete()
        item = pedido.itens.get()
        self.assertIsNone(item.produto)
        self.assertEqual(item.nome_produto, 'Pera')

    def test_cliente_nao_ve_pedidos_de_outro_cliente(self):
        pedido = criar_pedido(self.outro_cliente, self.loja, self.produto, 'Pendente')
        self.client.force_authenticate(self.cliente)
        lista = self.client.get('/api/v1/pedidos/')
        detalhe = self.client.get(f'/api/v1/pedidos/{pedido.pedido_id}/')
        self.assertEqual(len(lista.data), 0)
        self.assertEqual(detalhe.status_code, 404)

    def test_produtor_ve_apenas_os_pedidos_da_propria_loja(self):
        propria = criar_pedido(self.cliente, self.loja, self.produto, 'Pendente')
        criar_pedido(self.cliente, self.outra_loja, self.produto_outra_loja, 'Pendente')
        self.client.force_authenticate(self.produtor)
        response = self.client.get('/api/v1/pedidos/minha-loja/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['pedido_id'], propria.pedido_id)

    def test_produtor_nao_pula_etapas_do_status(self):
        pedido = criar_pedido(self.cliente, self.loja, self.produto, 'Em preparo')
        entregue = criar_status('Entregue')
        self.client.force_authenticate(self.produtor)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/status/', {'status': entregue.status_pedido_id}, format='json')
        self.assertEqual(response.status_code, 400)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status.status, 'Em preparo')

    def test_cliente_cancela_pedido_pendente_e_o_estoque_volta(self):
        pedido = criar_pedido(self.cliente, self.loja, self.produto, 'Pendente', quantidade=2)
        self.client.force_authenticate(self.cliente)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/cancelar/')
        self.assertEqual(response.status_code, 200)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 12)

    def test_cliente_nao_cancela_pedido_em_preparo(self):
        pedido = criar_pedido(self.cliente, self.loja, self.produto, 'Em preparo')
        self.client.force_authenticate(self.cliente)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/cancelar/')
        self.assertEqual(response.status_code, 400)

    def test_cliente_nao_cancela_pedido_de_outro_cliente(self):
        pedido = criar_pedido(self.outro_cliente, self.loja, self.produto, 'Pendente')
        self.client.force_authenticate(self.cliente)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/cancelar/')
        self.assertEqual(response.status_code, 404)

    def test_produtor_cancela_pedido_e_o_estoque_volta(self):
        pedido = criar_pedido(self.cliente, self.loja, self.produto, 'Pendente', quantidade=2)
        cancelado = criar_status('Cancelado')
        self.client.force_authenticate(self.produtor)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/status/', {'status': cancelado.status_pedido_id}, format='json')
        self.assertEqual(response.status_code, 200)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 12)

    def test_cliente_confirma_a_entrega_de_pedido_pronto_para_retirada(self):
        pedido = criar_pedido(self.cliente, self.loja, self.produto, 'Pronto para retirada')
        self.client.force_authenticate(self.cliente)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/confirmar-entrega/')
        self.assertEqual(response.status_code, 200)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status.status, 'Entregue')

    def test_confirmacao_de_entrega_e_recusada_em_pedido_pendente(self):
        pedido = criar_pedido(self.cliente, self.loja, self.produto, 'Pendente')
        self.client.force_authenticate(self.cliente)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/confirmar-entrega/')
        self.assertEqual(response.status_code, 400)

    def test_cliente_nao_confirma_a_entrega_de_pedido_de_outro_cliente(self):
        pedido = criar_pedido(self.cliente, self.loja, self.produto, 'Pronto para retirada')
        self.client.force_authenticate(self.outro_cliente)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/confirmar-entrega/')
        self.assertEqual(response.status_code, 404)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status.status, 'Pronto para retirada')

    def test_produtor_ve_o_telefone_do_cliente_em_pedido_aberto(self):
        Telefone.objects.create(
            usuario=self.cliente, tipo=TipoTelefone.objects.get(descricao='Celular'), numero='51999990000', e_principal=True,
        )
        criar_pedido(self.cliente, self.loja, self.produto, 'Pendente')
        self.client.force_authenticate(self.produtor)
        response = self.client.get('/api/v1/pedidos/minha-loja/')
        self.assertEqual(response.data[0]['cliente']['telefone'], '51999990000')

    def test_produtor_de_outra_loja_nao_muda_o_status_do_pedido(self):
        pedido = criar_pedido(self.cliente, self.loja, self.produto, 'Pendente')
        em_preparo = criar_status('Em preparo')
        self.client.force_authenticate(self.outro_produtor)
        response = self.client.patch(f'/api/v1/pedidos/{pedido.pedido_id}/status/', {'status': em_preparo.status_pedido_id}, format='json')
        self.assertEqual(response.status_code, 404)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status.status, 'Pendente')
