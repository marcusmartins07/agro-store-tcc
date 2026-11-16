from django.test import TestCase

from .models import Genero, TipoTelefone


class DadosIniciaisTests(TestCase):
    def test_banco_migrado_possui_generos_e_tipos_de_telefone_padrao(self):
        self.assertEqual(Genero.objects.get(id_genero='M').genero, 'Masculino')
        self.assertEqual(Genero.objects.get(id_genero='F').genero, 'Feminino')
        self.assertEqual(Genero.objects.get(id_genero='I').genero, 'Prefiro não informar')
        self.assertTrue(TipoTelefone.objects.filter(descricao='Celular').exists())
        self.assertTrue(TipoTelefone.objects.filter(descricao='Fixo').exists())
        self.assertTrue(TipoTelefone.objects.filter(descricao='Comercial').exists())
