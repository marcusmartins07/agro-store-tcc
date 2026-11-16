from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('favoritos', '0001_initial'),
        ('produtos', '0003_sem_codigo_barras_e_integridade'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='favorito',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='favorito',
            constraint=models.UniqueConstraint(fields=('usuario', 'produto'), name='uq_favorito_usuario_produto'),
        ),
    ]
