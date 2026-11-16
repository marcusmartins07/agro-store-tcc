import django.db.models.deletion
import django.db.models.functions.text
import django.db.models.lookups
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('avaliacoes', '0001_initial'),
        ('pedidos', '0002_integridade_modelo_logico'),
        ('produtos', '0003_sem_codigo_barras_e_integridade'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='avaliacao',
            name='pedido_produto',
            field=models.OneToOneField(
                db_column='id_pedido_produto',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='avaliacao',
                to='pedidos.pedidoproduto',
            ),
        ),
        migrations.AlterField(
            model_name='avaliacao',
            name='usuario',
            field=models.ForeignKey(
                db_column='id_usuario', on_delete=django.db.models.deletion.PROTECT, related_name='avaliacoes', to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddConstraint(
            model_name='avaliacao',
            constraint=models.CheckConstraint(condition=models.Q(('nota__range', (1, 5))), name='avaliacao_nota_check'),
        ),
        migrations.AddConstraint(
            model_name='avaliacao',
            constraint=models.CheckConstraint(
                condition=django.db.models.lookups.LessThanOrEqual(django.db.models.functions.text.Length('comentario'), 500),
                name='ck_avaliacao_comentario_tamanho',
                violation_error_message='O comentário deve ter no máximo 500 caracteres.',
            ),
        ),
    ]
