import shutil
import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import override_settings
from rest_framework.test import APITestCase

from agrostore.usuarios.models import Genero, Usuario
from .models import Loja

MEDIA_ROOT_TESTES = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT_TESTES)
class LojasTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT_TESTES, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        genero = Genero.objects.get(id_genero='M')
        self.produtor = Usuario.objects.create_user(
            cpf='12345678901', email='produtor@example.com', password='senha123', nome='Produtor',
            data_nascimento=date(1990, 1, 1), genero=genero, is_produtor=True,
        )
        self.outro_produtor = Usuario.objects.create_user(
            cpf='12345678902', email='outro@example.com', password='senha123', nome='Outro Produtor',
            data_nascimento=date(1990, 1, 1), genero=genero, is_produtor=True,
        )
        self.loja = Loja.objects.create(proprietario=self.produtor, nome='Feira Verde', cnpj='12345678000199')

    def test_produtor_nao_cria_segunda_loja(self):
        self.client.force_authenticate(self.produtor)
        response = self.client.post('/api/v1/lojas/lojas/', {'nome': 'Segunda Loja', 'cnpj': '98765432000198'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Loja.objects.filter(proprietario=self.produtor).count(), 1)

    def test_produtor_atualiza_nome_descricao_e_status_da_propria_loja(self):
        self.client.force_authenticate(self.produtor)
        dados = {'nome': 'Sitio Boa Terra', 'descricao': 'Produtos frescos', 'ativa': False}
        response = self.client.patch('/api/v1/lojas/eu/', dados, format='json')
        self.assertEqual(response.status_code, 200)
        self.loja.refresh_from_db()
        self.assertEqual(self.loja.nome, 'Sitio Boa Terra')
        self.assertEqual(self.loja.descricao, 'Produtos frescos')
        self.assertFalse(self.loja.ativa)

    def test_cnpj_nao_e_alterado_pela_edicao(self):
        self.client.force_authenticate(self.produtor)
        response = self.client.patch('/api/v1/lojas/eu/', {'cnpj': '98765432000198'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.loja.refresh_from_db()
        self.assertEqual(self.loja.cnpj, '12345678000199')

    def test_rota_por_id_nao_permite_editar_loja(self):
        self.client.force_authenticate(self.outro_produtor)
        response = self.client.patch(f'/api/v1/lojas/lojas/{self.loja.loja_id}/', {'nome': 'Invadida'}, format='json')
        self.assertEqual(response.status_code, 405)

    def test_banco_recusa_segunda_loja_do_mesmo_proprietario(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Loja.objects.create(proprietario=self.produtor, nome='Segunda Loja', cnpj='98765432000198')

    def test_nao_exclui_usuario_produtor_que_tem_loja(self):
        with self.assertRaises(ProtectedError):
            self.produtor.delete()
        self.assertTrue(Loja.objects.filter(pk=self.loja.pk).exists())

    def test_envio_de_imagem_da_loja_sem_login_retorna_401(self):
        imagem = SimpleUploadedFile('loja.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 32, content_type='image/png')
        response = self.client.patch('/api/v1/lojas/eu/', {'imagem_perfil': imagem}, format='multipart')
        self.assertEqual(response.status_code, 401)

    def test_imagem_da_loja_com_conteudo_que_nao_e_imagem_e_recusada_e_a_atual_e_mantida(self):
        nome_atual = 'lojas/' + 'a' * 32 + '.png'
        Loja.objects.filter(pk=self.loja.pk).update(imagem_perfil=nome_atual)
        self.client.force_authenticate(self.produtor)
        arquivo = SimpleUploadedFile('loja.png', b'texto simples', content_type='image/png')
        response = self.client.patch('/api/v1/lojas/eu/', {'imagem_perfil': arquivo}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['imagem_perfil'], ['Envie uma imagem JPG, PNG ou WEBP válida.'])
        self.loja.refresh_from_db()
        self.assertEqual(self.loja.imagem_perfil.name, nome_atual)
