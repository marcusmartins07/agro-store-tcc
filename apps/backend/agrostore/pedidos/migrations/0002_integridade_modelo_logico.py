from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lojas', '0001_initial'),
        ('pedidos', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='pedido',
            constraint=models.CheckConstraint(condition=models.Q(('valor_bruto__gte', 0)), name='pedido_valor_bruto_check'),
        ),
        migrations.AddConstraint(
            model_name='pedido',
            constraint=models.CheckConstraint(condition=models.Q(('valor_desconto__gte', 0)), name='pedido_valor_desconto_check'),
        ),
        migrations.AddConstraint(
            model_name='pedido',
            constraint=models.CheckConstraint(condition=models.Q(('valor_liquido__gte', 0)), name='pedido_valor_liquido_check'),
        ),
    ]
