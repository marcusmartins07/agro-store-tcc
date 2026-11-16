from django.db import connection
from django.test import TestCase


class SchemaTests(TestCase):
    def test_tabelas_do_modelo_logico_existem(self):
        esperadas = [
            'genero', 'usuario', 'redefinicao_senha', 'tipo_telefone', 'telefone', 'loja', 'categoria', 'produto',
            'preco_produto', 'imagem', 'carrinho', 'carrinho_produto', 'status_pedido', 'pedido', 'pedido_cliente',
            'pedido_produto', 'favorito', 'avaliacao',
        ]
        existentes = connection.introspection.table_names()
        self.assertTrue(set(esperadas).issubset(set(existentes)))

    def test_tabela_usuario_tem_as_colunas_esperadas(self):
        esperadas = [
            'id_usuario', 'nome', 'cpf', 'email', 'data_nascimento', 'foto_perfil', 'senha', 'ultimo_login',
            'e_produtor', 'esta_ativo', 'e_equipe', 'e_superusuario', 'codigo_genero',
        ]
        with connection.cursor() as cursor:
            descricao = connection.introspection.get_table_description(cursor, 'usuario')
        colunas = [coluna.name for coluna in descricao]
        self.assertTrue(set(esperadas).issubset(set(colunas)))
