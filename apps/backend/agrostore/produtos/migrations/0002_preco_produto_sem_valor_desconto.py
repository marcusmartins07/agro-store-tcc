from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations


def recalcular_porcentagem_vigente(apps, schema_editor):
    PrecoProduto = apps.get_model('produtos', 'PrecoProduto')
    for preco in PrecoProduto.objects.filter(vigencia_fim__isnull=True):
        porcentagem = preco.porcentagem_desconto or 0
        if preco.preco_venda and preco.preco_desconto is not None:
            proporcao = preco.preco_desconto / preco.preco_venda * 100
            porcentagem = int(proporcao.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        porcentagem = min(max(porcentagem, 0), 100)
        if porcentagem != preco.porcentagem_desconto:
            PrecoProduto.objects.filter(pk=preco.pk).update(porcentagem_desconto=porcentagem)


def restaurar_valor_desconto(apps, schema_editor):
    PrecoProduto = apps.get_model('produtos', 'PrecoProduto')
    for preco in PrecoProduto.objects.all():
        porcentagem = Decimal(preco.porcentagem_desconto or 0)
        valor = (preco.preco_venda * porcentagem / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        PrecoProduto.objects.filter(pk=preco.pk).update(preco_desconto=valor)


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(recalcular_porcentagem_vigente, restaurar_valor_desconto),
        migrations.RemoveField(
            model_name='precoproduto',
            name='preco_desconto',
        ),
    ]
