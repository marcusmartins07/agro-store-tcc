from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from agrostore.favoritos.models import Favorito
from agrostore.lojas.models import Loja
from agrostore.produtos.models import Categoria, PrecoProduto, Produto
from agrostore.usuarios.models import Genero, Usuario


class FavoritosTests(APITestCase):
    def setUp(self):
        genero = Genero.objects.get(id_genero='M')
        self.produtor = Usuario.objects.create_user(
            cpf='12345678901', email='produtor@example.com', password='senha123', nome='Produtor',
            data_nascimento=date(1990, 1, 1), genero=genero, is_produtor=True,
        )
        self.cliente = Usuario.objects.create_user(
            cpf='12345678902', email='cliente@example.com', password='senha123', nome='Cliente',
            data_nascimento=date(1990, 1, 1), genero=genero,
        )
        self.outro_cliente = Usuario.objects.create_user(
            cpf='12345678903', email='outro@example.com', password='senha123', nome='Outro',
            data_nascimento=date(1990, 1, 1), genero=genero,
        )
        loja = Loja.objects.create(proprietario=self.produtor, nome='Feira Verde', cnpj='12345678000199')
        categoria = Categoria.objects.create(nome='Frutas')
        self.produto = Produto.objects.create(loja=loja, nome='Maca', estoque=8, categoria=categoria)
        PrecoProduto.objects.create(produto=self.produto, preco_venda=Decimal('10.00'), porcentagem_desconto=10)

    def test_endpoints_exigem_autenticacao(self):
        response = self.client.get('/api/v1/favoritos/')
        self.assertEqual(response.status_code, 401)

    def test_cliente_cria_favorito(self):
        self.client.force_authenticate(self.cliente)
        response = self.client.post('/api/v1/favoritos/', {'produto': self.produto.produto_id}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['dados_produto']['nome'], 'Maca')

    def test_listagem_retorna_so_os_favoritos_do_usuario(self):
        Favorito.objects.create(usuario=self.cliente, produto=self.produto)
        self.client.force_authenticate(self.outro_cliente)
        response = self.client.get('/api/v1/favoritos/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_produto_nao_pode_ser_favoritado_duas_vezes(self):
        Favorito.objects.create(usuario=self.cliente, produto=self.produto)
        self.client.force_authenticate(self.cliente)
        response = self.client.post('/api/v1/favoritos/', {'produto': self.produto.produto_id}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, ['Produto já está nos favoritos.'])

    def test_usuario_nao_remove_favorito_de_outro_usuario(self):
        favorito = Favorito.objects.create(usuario=self.cliente, produto=self.produto)
        self.client.force_authenticate(self.outro_cliente)
        response = self.client.delete(f'/api/v1/favoritos/{favorito.pk}/')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Favorito.objects.filter(pk=favorito.pk).exists())
