from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('carrinhos', '0001_initial'),
        ('lojas', '0001_initial'),
        ('produtos', '0003_sem_codigo_barras_e_integridade'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='carrinho',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='carrinhoproduto',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='carrinho',
            constraint=models.UniqueConstraint(fields=('usuario', 'loja'), name='uq_carrinho_usuario_loja'),
        ),
        migrations.AddConstraint(
            model_name='carrinho',
            constraint=models.CheckConstraint(condition=models.Q(('valor_bruto__gte', 0)), name='carrinho_valor_bruto_check'),
        ),
        migrations.AddConstraint(
            model_name='carrinho',
            constraint=models.CheckConstraint(condition=models.Q(('valor_desconto__gte', 0)), name='carrinho_valor_desconto_check'),
        ),
        migrations.AddConstraint(
            model_name='carrinho',
            constraint=models.CheckConstraint(condition=models.Q(('valor_liquido__gte', 0)), name='carrinho_valor_liquido_check'),
        ),
        migrations.AddConstraint(
            model_name='carrinhoproduto',
            constraint=models.UniqueConstraint(fields=('carrinho', 'produto'), name='uq_carrinho_produto'),
        ),
    ]
