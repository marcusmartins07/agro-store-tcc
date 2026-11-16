from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_dados_iniciais'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='redefinicaosenha',
            name='redefinicao_senha_expiracao_apos_criacao',
        ),
        migrations.AddConstraint(
            model_name='redefinicaosenha',
            constraint=models.CheckConstraint(
                condition=models.Q(('data_expiracao__gt', models.F('data_criacao'))),
                name='ck_redefinicao_senha_expiracao',
            ),
        ),
    ]
