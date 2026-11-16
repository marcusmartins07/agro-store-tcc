import django.db.models.deletion
from django.db import migrations, models


def gerar_sku_ausente(apps, schema_editor):
    Produto = apps.get_model('produtos', 'Produto')
    for produto in Produto.objects.filter(models.Q(sku__isnull=True) | models.Q(sku='')):
        componentes = (
            ('loja', produto.loja_id, 4),
            ('categoria', produto.categoria_id, 4),
            ('produto', produto.pk, 6),
        )
        for nome, valor, tamanho in componentes:
            if valor > (10 ** tamanho) - 1:
                raise ValueError(f'Identificador de {nome} excede o limite de {tamanho} dígitos para o SKU.')
        sku = ''.join(f'{valor:0{tamanho}d}' for _, valor, tamanho in componentes)
        Produto.objects.filter(pk=produto.pk).update(sku=sku)


class Migration(migrations.Migration):

    dependencies = [
        ('lojas', '0001_initial'),
        ('produtos', '0002_preco_produto_sem_valor_desconto'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='produto',
            name='codigo_barras',
        ),
        migrations.AlterField(
            model_name='precoproduto',
            name='produto',
            field=models.ForeignKey(
                db_column='id_produto', on_delete=django.db.models.deletion.PROTECT, related_name='precos', to='produtos.produto'
            ),
        ),
        migrations.AlterField(
            model_name='produto',
            name='loja',
            field=models.ForeignKey(
                db_column='id_loja', on_delete=django.db.models.deletion.PROTECT, related_name='produtos', to='lojas.loja'
            ),
        ),
        migrations.RunPython(gerar_sku_ausente, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='produto',
            name='sku',
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
        migrations.AddConstraint(
            model_name='imagemproduto',
            constraint=models.UniqueConstraint(fields=('produto', 'ordem'), name='uq_imagem_produto_ordem'),
        ),
        migrations.AddConstraint(
            model_name='precoproduto',
            constraint=models.CheckConstraint(condition=models.Q(('preco_venda__gte', 0)), name='preco_produto_valor_venda_check'),
        ),
        migrations.AddConstraint(
            model_name='precoproduto',
            constraint=models.CheckConstraint(condition=models.Q(('preco_custo__gte', 0)), name='preco_produto_valor_custo_check'),
        ),
        migrations.AddConstraint(
            model_name='precoproduto',
            constraint=models.CheckConstraint(
                condition=models.Q(('porcentagem_desconto__range', (0, 100))),
                name='preco_produto_porcentagem_desconto_check',
            ),
        ),
        migrations.AddConstraint(
            model_name='precoproduto',
            constraint=models.CheckConstraint(
                condition=models.Q(('vigencia_fim__isnull', True), ('vigencia_fim__gte', models.F('vigencia_inicio')), _connector='OR'),
                name='ck_preco_vigencia',
            ),
        ),
        migrations.AddConstraint(
            model_name='produto',
            constraint=models.CheckConstraint(condition=models.Q(('estoque__gte', 0)), name='produto_estoque_check'),
        ),
    ]
