import hashlib
from datetime import date, timedelta

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Genero, RedefinicaoSenha, TipoTelefone, Usuario


def criar_usuario(cpf='11144477735', email='existente@example.com'):
    return Usuario.objects.create_user(
        cpf=cpf, email=email, password='SenhaForte123', nome='Usuario Existente',
        data_nascimento=date(2000, 1, 1), genero=Genero.objects.get(id_genero='M'),
    )


@override_settings(FRONTEND_URL='http://front.test')
class UsuariosTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.dados = {
            'nome': 'Cliente de Teste', 'cpf': '529.982.247-25', 'email': 'cliente@example.com',
            'telefone': '(51) 99999-0000', 'tipo_telefone': TipoTelefone.objects.get(descricao='Celular').pk,
            'data_nascimento': '2000-05-10', 'genero': 'M',
            'password': 'SenhaForte123', 'password_confirmacao': 'SenhaForte123',
        }

    def test_cadastro_valido_retorna_tokens(self):
        response = self.client.post('/api/v1/usuarios/cadastro/', self.dados, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_cadastro_recusa_cpf_invalido(self):
        self.dados['cpf'] = '111.111.111-11'
        response = self.client.post('/api/v1/usuarios/cadastro/', self.dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('cpf', response.data)

    def test_cadastro_recusa_cpf_duplicado(self):
        criar_usuario(cpf='52998224725')
        response = self.client.post('/api/v1/usuarios/cadastro/', self.dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('cpf', response.data)

    def test_cadastro_recusa_email_duplicado(self):
        criar_usuario(email='cliente@example.com')
        response = self.client.post('/api/v1/usuarios/cadastro/', self.dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_cadastro_recusa_confirmacao_de_senha_diferente(self):
        self.dados['password_confirmacao'] = 'OutraSenha123'
        response = self.client.post('/api/v1/usuarios/cadastro/', self.dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('password_confirmacao', response.data)

    def test_cadastro_recusa_menor_de_16_anos(self):
        self.dados['data_nascimento'] = (date.today() - timedelta(days=15 * 365)).isoformat()
        response = self.client.post('/api/v1/usuarios/cadastro/', self.dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('data_nascimento', response.data)

    def test_cadastro_ignora_campos_de_privilegio(self):
        self.dados['is_produtor'] = True
        self.dados['is_staff'] = True
        response = self.client.post('/api/v1/usuarios/cadastro/', self.dados, format='json')
        self.assertEqual(response.status_code, 201)
        usuario = Usuario.objects.get(cpf='52998224725')
        self.assertFalse(usuario.is_produtor)
        self.assertFalse(usuario.is_staff)

    def test_login_com_cpf_e_senha_corretos_retorna_tokens(self):
        criar_usuario()
        response = self.client.post('/api/v1/usuarios/login/', {'cpf': '11144477735', 'password': 'SenhaForte123'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_com_senha_errada_e_recusado(self):
        criar_usuario()
        response = self.client.post('/api/v1/usuarios/login/', {'cpf': '11144477735', 'password': 'SenhaErrada123'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('access', response.data)

    def test_perfil_atualiza_dados_pessoais(self):
        self.client.force_authenticate(criar_usuario())
        response = self.client.patch('/api/v1/usuarios/eu/', {'nome': 'Nome Novo', 'genero': 'F'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nome'], 'Nome Novo')
        self.assertEqual(response.data['genero'], 'F')

    def test_perfil_nao_altera_cpf_nem_privilegios(self):
        usuario = criar_usuario()
        self.client.force_authenticate(usuario)
        response = self.client.patch('/api/v1/usuarios/eu/', {'cpf': '52998224725', 'is_produtor': True}, format='json')
        self.assertEqual(response.status_code, 400)
        usuario.refresh_from_db()
        self.assertEqual(usuario.cpf, '11144477735')
        self.assertFalse(usuario.is_produtor)

    def test_perfil_sem_login_retorna_401(self):
        response = self.client.patch('/api/v1/usuarios/eu/', {'nome': 'Sem login'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_redefinicao_envia_email_com_link(self):
        criar_usuario(email='cliente@example.com')
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post('/api/v1/usuarios/redefinir-senha/', {'email': 'cliente@example.com'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('http://front.test/redefinir-senha#token=', mail.outbox[0].body)

    def test_redefinicao_confirmada_troca_a_senha(self):
        usuario = criar_usuario()
        RedefinicaoSenha.objects.create(
            usuario=usuario, token_hash=hashlib.sha256(b'token-teste').hexdigest(),
            data_expiracao=timezone.now() + timedelta(minutes=30),
        )
        dados = {'token': 'token-teste', 'password': 'NovaSenhaSegura456', 'password_confirmacao': 'NovaSenhaSegura456'}
        response = self.client.post('/api/v1/usuarios/redefinir-senha/confirmar/', dados, format='json')
        self.assertEqual(response.status_code, 200)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('NovaSenhaSegura456'))

    def test_redefinicao_com_link_ja_usado_e_recusada(self):
        usuario = criar_usuario()
        RedefinicaoSenha.objects.create(
            usuario=usuario, token_hash=hashlib.sha256(b'token-usado').hexdigest(),
            data_expiracao=timezone.now() + timedelta(minutes=30), data_utilizacao=timezone.now(),
        )
        dados = {'token': 'token-usado', 'password': 'NovaSenhaSegura456', 'password_confirmacao': 'NovaSenhaSegura456'}
        response = self.client.post('/api/v1/usuarios/redefinir-senha/confirmar/', dados, format='json')
        self.assertEqual(response.status_code, 400)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('SenhaForte123'))

    def test_redefinicao_com_link_expirado_e_recusada(self):
        usuario = criar_usuario()
        redefinicao = RedefinicaoSenha.objects.create(
            usuario=usuario, token_hash=hashlib.sha256(b'token-expirado').hexdigest(),
            data_expiracao=timezone.now() + timedelta(minutes=30),
        )
        agora = timezone.now()
        RedefinicaoSenha.objects.filter(pk=redefinicao.pk).update(
            data_criacao=agora - timedelta(minutes=31), data_expiracao=agora - timedelta(minutes=1),
        )
        dados = {'token': 'token-expirado', 'password': 'NovaSenhaSegura456', 'password_confirmacao': 'NovaSenhaSegura456'}
        response = self.client.post('/api/v1/usuarios/redefinir-senha/confirmar/', dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Este link de redefinição é inválido ou expirou. Solicite um novo.')
        redefinicao.refresh_from_db()
        self.assertIsNone(redefinicao.data_utilizacao)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('SenhaForte123'))

    def test_redefinicao_recusa_a_sexta_solicitacao_do_mesmo_endereco_na_mesma_hora(self):
        for _ in range(5):
            response = self.client.post('/api/v1/usuarios/redefinir-senha/', {'email': 'inexistente@example.com'}, format='json')
            self.assertEqual(response.status_code, 200)
        response = self.client.post('/api/v1/usuarios/redefinir-senha/', {'email': 'inexistente@example.com'}, format='json')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data['detail'], 'Muitas solicitações. Tente novamente mais tarde.')
