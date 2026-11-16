from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from agrostore.carrinhos.models import Carrinho, CarrinhoProduto
from agrostore.lojas.models import Loja
from agrostore.produtos.models import Categoria, PrecoProduto, Produto
from agrostore.usuarios.models import Genero, Usuario


def criar_usuario(cpf, email, is_produtor=False):
    return Usuario.objects.create_user(
        cpf=cpf, email=email, password='senha123', nome=email.split('@')[0],
        data_nascimento=date(1990, 1, 1), genero=Genero.objects.get(id_genero='M'), is_produtor=is_produtor,
    )


class CarrinhosTests(APITestCase):
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
        self.client.force_authenticate(self.cliente)

    def test_adiciona_produto_e_confere_os_totais_do_carrinho(self):
        response = self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 2}, format='json')
        self.assertEqual(response.status_code, 201)
        carrinho = Carrinho.objects.get(usuario=self.cliente)
        self.assertEqual(carrinho.valor_bruto, Decimal('20.00'))
        self.assertEqual(carrinho.valor_desconto, Decimal('2.00'))
        self.assertEqual(carrinho.valor_liquido, Decimal('18.00'))

    def test_recusa_usuario_nao_autenticado(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 1}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_recusa_produto_inativo(self):
        Produto.objects.filter(pk=self.produto.pk).update(ativo=False)
        response = self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 1}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CarrinhoProduto.objects.exists())

    def test_recusa_produto_de_loja_inativa(self):
        Loja.objects.filter(pk=self.loja.pk).update(ativa=False)
        response = self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 1}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['produto'], ['Produto de loja inativa não pode ser adicionado ao carrinho.'])
        self.assertFalse(CarrinhoProduto.objects.exists())

    def test_recusa_quantidade_acima_do_estoque(self):
        response = self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 11}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Produto sem estoque suficiente para a quantidade solicitada.')

    def test_recusa_produto_sem_estoque(self):
        Produto.objects.filter(pk=self.produto.pk).update(estoque=0)
        response = self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 1}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CarrinhoProduto.objects.exists())

    def test_adicionar_produto_repetido_soma_a_quantidade(self):
        self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 2}, format='json')
        self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 3}, format='json')
        item = CarrinhoProduto.objects.get()
        self.assertEqual(item.quantidade, 5)

    def test_lista_so_os_carrinhos_do_usuario_autenticado(self):
        carrinho_outro = Carrinho.objects.create(usuario=self.outro_cliente, loja=self.loja)
        CarrinhoProduto.objects.create(carrinho=carrinho_outro, produto=self.produto, quantidade=1)
        carrinho = Carrinho.objects.create(usuario=self.cliente, loja=self.outra_loja)
        CarrinhoProduto.objects.create(carrinho=carrinho, produto=self.produto_outra_loja, quantidade=1)
        response = self.client.get('/api/v1/carrinhos/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['carrinho_id'], carrinho.carrinho_id)

    def test_recusa_atualizar_item_para_quantidade_zero(self):
        carrinho = Carrinho.objects.create(usuario=self.cliente, loja=self.loja)
        item = CarrinhoProduto.objects.create(carrinho=carrinho, produto=self.produto, quantidade=2)
        response = self.client.patch(f'/api/v1/carrinhos/itens/{item.carrinho_produto_id}/', {'quantidade': 0}, format='json')
        self.assertEqual(response.status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 2)

    def test_nao_atualiza_item_de_outro_usuario(self):
        carrinho = Carrinho.objects.create(usuario=self.outro_cliente, loja=self.loja)
        item = CarrinhoProduto.objects.create(carrinho=carrinho, produto=self.produto, quantidade=2)
        response = self.client.patch(f'/api/v1/carrinhos/itens/{item.carrinho_produto_id}/', {'quantidade': 5}, format='json')
        self.assertEqual(response.status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 2)

    def test_produtos_de_lojas_diferentes_criam_carrinhos_separados(self):
        self.client.post('/api/v1/carrinhos/', {'produto': self.produto.produto_id, 'quantidade': 1}, format='json')
        self.client.post('/api/v1/carrinhos/', {'produto': self.produto_outra_loja.produto_id, 'quantidade': 1}, format='json')
        self.assertEqual(Carrinho.objects.filter(usuario=self.cliente).count(), 2)
