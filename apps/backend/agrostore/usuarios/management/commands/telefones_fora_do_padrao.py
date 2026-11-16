from django.core.management.base import BaseCommand

from agrostore.usuarios.models import Telefone
from agrostore.usuarios.telefones import numero_respeita_tipo


class Command(BaseCommand):
    help = (
        'Lista, somente para leitura, os telefones cuja quantidade de dígitos não respeita o tipo (RN-021). '
        'Exibe ids, tipo e quantidade de dígitos, nunca o número.'
    )

    def handle(self, *args, **options):
        quantidade = 0
        for telefone in Telefone.objects.select_related('tipo').order_by('usuario_id', 'id').iterator():
            if numero_respeita_tipo(telefone.numero, telefone.tipo):
                continue
            quantidade += 1
            self.stdout.write(
                f'usuario={telefone.usuario_id} telefone={telefone.id} tipo={telefone.tipo.descricao} '
                f'digitos={len(telefone.numero)}'
            )

        if quantidade == 0:
            self.stdout.write(self.style.SUCCESS('Nenhum telefone fora do padrão.'))
            return
        self.stdout.write(self.style.WARNING(f'{quantidade} telefone(s) fora do padrão. Corrija pela área administrativa.'))
