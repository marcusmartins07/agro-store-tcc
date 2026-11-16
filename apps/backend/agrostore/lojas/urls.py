from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LojaViewSet, MinhaLojaImagemView, MinhaLojaView

router = DefaultRouter()
router.register('lojas', LojaViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('eu/', MinhaLojaView.as_view()),
    path('eu/imagem/', MinhaLojaImagemView.as_view()),
]
