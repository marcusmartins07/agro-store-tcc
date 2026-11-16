from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CadastroClienteView,
    ConfirmacaoRedefinicaoSenhaView,
    EuView,
    LoginView,
    MinhaFotoView,
    SolicitacaoRedefinicaoSenhaView,
    TelefoneViewSet,
)

router = SimpleRouter()
router.register('eu/telefones', TelefoneViewSet, basename='telefone')


urlpatterns = [
    path('cadastro/', CadastroClienteView.as_view(), name='cadastro-cliente'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('eu/', EuView.as_view(), name='eu'),
    path('eu/foto/', MinhaFotoView.as_view(), name='eu-foto'),
    path('redefinir-senha/', SolicitacaoRedefinicaoSenhaView.as_view(), name='redefinir-senha'),
    path('redefinir-senha/confirmar/', ConfirmacaoRedefinicaoSenhaView.as_view(), name='redefinir-senha-confirmar'),
    *router.urls,
]
