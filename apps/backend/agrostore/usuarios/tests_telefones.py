from datetime import date

from rest_framework.test import APITestCase

from .models import Genero, Telefone, TipoTelefone, Usuario


def criar_usuario(cpf, email):
    return Usuario.objects.create_user(
        cpf=cpf, email=email, password='SenhaForte123', nome='Usuario Telefone',
        data_nascimento=date(2000, 1, 1), genero=Genero.objects.get(id_genero='M'),
    )


class TelefonesTests(APITestCase):
    def setUp(self):
        self.celular = TipoTelefone.objects.get(descricao='Celular')
        self.fixo = TipoTelefone.objects.get(descricao='Fixo')
        self.usuario = criar_usuario('52998224725', 'tel@example.com')
        self.outro = criar_usuario('11144477735', 'outro@example.com')
        self.principal = Telefone.objects.create(usuario=self.usuario, tipo=self.celular, numero='51999990000', e_principal=True)
        self.client.force_authenticate(self.usuario)

    def test_tipos_de_telefone_sao_listados_sem_autenticacao(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/v1/tipos-telefone/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    def test_cadastro_retorna_telefone_principal_com_tipo(self):
        dados = {
            'nome': 'Cliente Novo', 'cpf': '39053344705', 'email': 'novo@example.com', 'telefone': '(51) 99999-0000',
            'tipo_telefone': self.celular.pk, 'data_nascimento': '2000-05-10', 'genero': 'M',
            'password': 'SenhaForte123', 'password_confirmacao': 'SenhaForte123',
        }
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/v1/usuarios/cadastro/', dados, format='json')
        self.assertEqual(response.status_code, 201)
        telefone = response.data['usuario']['telefones'][0]
        self.assertEqual(telefone['numero'], '51999990000')
        self.assertEqual(telefone['tipo_descricao'], 'Celular')
        self.assertTrue(telefone['e_principal'])

    def test_cadastro_recusa_quantidade_de_digitos_invalida(self):
        dados = {
            'nome': 'Cliente Novo', 'cpf': '39053344705', 'email': 'novo@example.com', 'telefone': '5133334444',
            'tipo_telefone': self.celular.pk, 'data_nascimento': '2000-05-10', 'genero': 'M',
            'password': 'SenhaForte123', 'password_confirmacao': 'SenhaForte123',
        }
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/v1/usuarios/cadastro/', dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('telefone', response.data)

    def test_telefone_de_outro_usuario_retorna_404(self):
        alheio = Telefone.objects.create(usuario=self.outro, tipo=self.celular, numero='51988887777', e_principal=True)
        response = self.client.get(f'/api/v1/usuarios/eu/telefones/{alheio.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_telefones_exigem_autenticacao(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/v1/usuarios/eu/telefones/')
        self.assertEqual(response.status_code, 401)

    def test_cria_telefone(self):
        dados = {'numero': '(51) 3333-4444', 'tipo': self.fixo.pk}
        response = self.client.post('/api/v1/usuarios/eu/telefones/', dados, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['numero'], '5133334444')

    def test_definir_outro_telefone_como_principal_desmarca_o_anterior(self):
        segundo = Telefone.objects.create(usuario=self.usuario, tipo=self.fixo, numero='5133334444', e_principal=False)
        response = self.client.patch(f'/api/v1/usuarios/eu/telefones/{segundo.pk}/', {'e_principal': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.principal.refresh_from_db()
        self.assertFalse(self.principal.e_principal)

    def test_nao_exclui_o_ultimo_telefone(self):
        response = self.client.delete(f'/api/v1/usuarios/eu/telefones/{self.principal.pk}/')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Telefone.objects.filter(pk=self.principal.pk).exists())
