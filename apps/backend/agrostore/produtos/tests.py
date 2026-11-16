import shutil
import tempfile
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from agrostore.carrinhos.models import Carrinho, CarrinhoProduto
from agrostore.lojas.models import Loja
from agrostore.usuarios.models import Genero, Usuario
from .models import Categoria, ImagemProduto, PrecoProduto, Produto

MEDIA_ROOT_TESTES = tempfile.mkdtemp()


def criar_usuario(cpf, email, is_produtor=False):
    return Usuario.objects.create_user(
        cpf=cpf, email=email, password='senha123', nome=email.split('@')[0],
        data_nascimento=date(1990, 1, 1), genero=Genero.objects.get(id_genero='M'), is_produtor=is_produtor,
    )


class ProdutosTests(APITestCase):
    def setUp(self):
        self.produtor = criar_usuario('12345678901', 'produtor@example.com', is_produtor=True)
        self.outro_produtor = criar_usuario('12345678902', 'outro@example.com', is_produtor=True)
        self.cliente = criar_usuario('12345678903', 'cliente@example.com')
        self.loja = Loja.objects.create(proprietario=self.produtor, nome='Feira Verde', cnpj='12345678000199')
        self.outra_loja = Loja.objects.create(proprietario=self.outro_produtor, nome='Sitio Outro', cnpj='12345678000288')
        self.categoria = Categoria.objects.create(nome='Frutas')
        self.produto = Produto.objects.create(loja=self.loja, nome='Maca', estoque=10, categoria=self.categoria)
        self.produto_outro = Produto.objects.create(loja=self.outra_loja, nome='Pera', estoque=10, categoria=self.categoria)
        self.dados = {'nome': 'Banana', 'descricao': 'Banana prata', 'categoria': self.categoria.categoria_id, 'estoque': 5}

    def test_criacao_gera_sku_com_ids_preenchidos_por_zeros(self):
        self.client.force_authenticate(self.produtor)
        response = self.client.post('/api/v1/produtos/', self.dados, format='json')
        self.assertEqual(response.status_code, 201)
        produto = Produto.objects.get(pk=response.data['produto_id'])
        esperado = f'{self.loja.loja_id:04d}{self.categoria.categoria_id:04d}{produto.produto_id:06d}'
        self.assertEqual(produto.sku, esperado)

    def test_sku_nao_muda_na_edicao(self):
        sku_original = self.produto.sku
        self.client.force_authenticate(self.produtor)
        response = self.client.patch(f'/api/v1/produtos/{self.produto.produto_id}/', {'nome': 'Maca Gala', 'sku': 'novo'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.sku, sku_original)

    def test_cliente_nao_cadastra_produto(self):
        self.client.force_authenticate(self.cliente)
        response = self.client.post('/api/v1/produtos/', self.dados, format='json')
        self.assertEqual(response.status_code, 403)

    def test_produtor_lista_so_os_proprios_produtos(self):
        self.client.force_authenticate(self.produtor)
        response = self.client.get('/api/v1/produtos/meus/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nome'], 'Maca')

    def test_produtor_nao_edita_produto_de_outra_loja(self):
        self.client.force_authenticate(self.produtor)
        response = self.client.patch(f'/api/v1/produtos/{self.produto_outro.produto_id}/', {'nome': 'Invadido'}, format='json')
        self.assertEqual(response.status_code, 404)
        self.produto_outro.refresh_from_db()
        self.assertEqual(self.produto_outro.nome, 'Pera')

    def test_criacao_exige_categoria(self):
        self.client.force_authenticate(self.produtor)
        del self.dados['categoria']
        response = self.client.post('/api/v1/produtos/', self.dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('categoria', response.data)

    def test_criacao_recusa_categoria_inativa(self):
        inativa = Categoria.objects.create(nome='Antiga', ativo=False)
        self.dados['categoria'] = inativa.categoria_id
        self.client.force_authenticate(self.produtor)
        response = self.client.post('/api/v1/produtos/', self.dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('categoria', response.data)

    def test_produtor_cria_sugestao_de_categoria_inativa(self):
        self.client.force_authenticate(self.produtor)
        response = self.client.post('/api/v1/produtos/categorias/', {'nome': 'Hortalicas'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(Categoria.objects.get(nome='Hortalicas').ativo)

    def test_estoque_negativo_e_recusado(self):
        self.client.force_authenticate(self.produtor)
        self.dados['estoque'] = -1
        response = self.client.post('/api/v1/produtos/', self.dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('estoque', response.data)

    def test_produto_sem_estoque_some_da_listagem_mas_o_detalhe_continua_acessivel(self):
        Produto.objects.filter(pk=self.produto.pk).update(estoque=0)
        listagem = self.client.get('/api/v1/produtos/')
        detalhe = self.client.get(f'/api/v1/produtos/{self.produto.produto_id}/')
        nomes = [item['nome'] for item in listagem.data]
        self.assertNotIn('Maca', nomes)
        self.assertIn('Pera', nomes)
        self.assertEqual(detalhe.status_code, 200)

    def test_reducao_de_estoque_ajusta_a_quantidade_dos_carrinhos(self):
        carrinho = Carrinho.objects.create(usuario=self.cliente, loja=self.loja)
        item = CarrinhoProduto.objects.create(carrinho=carrinho, produto=self.produto, quantidade=8)
        self.client.force_authenticate(self.produtor)
        response = self.client.patch(f'/api/v1/produtos/{self.produto.produto_id}/', {'estoque': 3}, format='json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 3)

    def test_preco_de_10_reais_com_20_por_cento_de_desconto_resulta_em_8(self):
        self.client.force_authenticate(self.produtor)
        dados = {'produto': self.produto.produto_id, 'preco_venda': '10.00', 'porcentagem_desconto': 20}
        response = self.client.post('/api/v1/produtos/precos/', dados, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Decimal(str(response.data['preco_final'])), Decimal('8.00'))

    def test_novo_preco_encerra_o_vigente(self):
        anterior = PrecoProduto.objects.create(produto=self.produto, preco_venda=Decimal('10.00'))
        self.client.force_authenticate(self.produtor)
        dados = {'produto': self.produto.produto_id, 'preco_venda': '12.00'}
        response = self.client.post('/api/v1/produtos/precos/', dados, format='json')
        self.assertEqual(response.status_code, 201)
        anterior.refresh_from_db()
        self.assertIsNotNone(anterior.vigencia_fim)
        self.assertEqual(PrecoProduto.objects.filter(produto=self.produto, vigencia_fim__isnull=True).count(), 1)

    def test_produtor_nao_cria_preco_para_produto_de_outra_loja(self):
        self.client.force_authenticate(self.produtor)
        dados = {'produto': self.produto_outro.produto_id, 'preco_venda': '10.00'}
        response = self.client.post('/api/v1/produtos/precos/', dados, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(PrecoProduto.objects.filter(produto=self.produto_outro).exists())

    def test_preco_custo_nao_aparece_para_visitante_anonimo(self):
        PrecoProduto.objects.create(produto=self.produto, preco_venda=Decimal('10.00'), preco_custo=Decimal('5.00'))
        response = self.client.get(f'/api/v1/produtos/{self.produto.produto_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('preco_custo', response.data)


@override_settings(MEDIA_ROOT=MEDIA_ROOT_TESTES)
class ImagensProdutoTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT_TESTES, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.produtor = criar_usuario('12345678901', 'produtor@example.com', is_produtor=True)
        self.outro_produtor = criar_usuario('12345678902', 'outro@example.com', is_produtor=True)
        loja = Loja.objects.create(proprietario=self.produtor, nome='Feira Verde', cnpj='12345678000199')
        categoria = Categoria.objects.create(nome='Frutas')
        self.produto = Produto.objects.create(loja=loja, nome='Maca', estoque=10, categoria=categoria)
        self.url = f'/api/v1/produtos/{self.produto.produto_id}/imagens/'

    def arquivo(self):
        return SimpleUploadedFile('maca.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 32, content_type='image/png')

    def test_primeira_imagem_enviada_vira_principal(self):
        self.client.force_authenticate(self.produtor)
        response = self.client.post(self.url, {'imagem': self.arquivo()}, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ImagemProduto.objects.get(produto=self.produto).e_principal)

    def test_sexta_imagem_e_recusada(self):
        for ordem in range(5):
            ImagemProduto.objects.create(produto=self.produto, imagem=f'produtos/{ordem}.png', ordem=ordem)
        self.client.force_authenticate(self.produtor)
        response = self.client.post(self.url, {'imagem': self.arquivo()}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ImagemProduto.objects.filter(produto=self.produto).count(), 5)

    def test_outro_produtor_nao_gerencia_as_imagens_do_produto(self):
        self.client.force_authenticate(self.outro_produtor)
        response = self.client.post(self.url, {'imagem': self.arquivo()}, format='multipart')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ImagemProduto.objects.filter(produto=self.produto).exists())

    def test_reordenar_imagens_aplica_a_nova_ordem_sem_violar_a_unicidade(self):
        primeira = ImagemProduto.objects.create(produto=self.produto, imagem='produtos/primeira.png', ordem=0)
        segunda = ImagemProduto.objects.create(produto=self.produto, imagem='produtos/segunda.png', ordem=1)
        terceira = ImagemProduto.objects.create(produto=self.produto, imagem='produtos/terceira.png', ordem=2)
        self.client.force_authenticate(self.produtor)
        response = self.client.post(f'{self.url}reordenar/', {'imagens': [terceira.id, primeira.id, segunda.id]}, format='json')
        self.assertEqual(response.status_code, 200)
        primeira.refresh_from_db()
        segunda.refresh_from_db()
        terceira.refresh_from_db()
        self.assertEqual((terceira.ordem, primeira.ordem, segunda.ordem), (0, 1, 2))
