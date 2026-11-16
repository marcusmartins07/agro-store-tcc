import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/services/api.js'
import { extrairMensagemErro } from '@/stores/index.js'
import { campoParaDecimal } from '@/utils/formatacao.js'
import { ordenarPorMaisRecente } from '@/utils/statusPedido.js'

const DIAS_GRAFICO = 7
const LIMITE_MAIS_VENDIDOS = 5

export const useProdutorStore = defineStore('produtor', () => {
  const loja = ref(null)
  const semLoja = ref(false)
  const produtos = ref([])
  const pedidos = ref([])
  const categorias = ref([])
  const statusIds = ref({})
  const carregando = ref(false)
  const carregado = ref(false)
  const erro = ref('')

  const produtosAtivos = computed(() => produtos.value.filter(produto => produto.ativo).length)
  const produtosInativos = computed(() => produtos.value.length - produtosAtivos.value)

  const pedidosOrdenados = computed(() => ordenarPorMaisRecente(pedidos.value))

  const pedidosPorStatus = computed(() => {
    const grupos = {}
    for (const pedido of pedidosOrdenados.value) {
      if (!grupos[pedido.status_nome]) grupos[pedido.status_nome] = []
      grupos[pedido.status_nome].push(pedido)
    }
    return grupos
  })

  const quantidadePendentes = computed(() => pedidos.value.filter(pedido => pedido.status_nome === 'Pendente').length)
  const quantidadeEmAndamento = computed(() =>
    pedidos.value.filter(pedido => pedido.status_nome === 'Em preparo' || pedido.status_nome === 'Pronto para retirada').length
  )

  const pedidosValidos = computed(() => pedidos.value.filter(pedido => pedido.status_nome !== 'Cancelado'))

  const pedidosDoMes = computed(() => {
    const hoje = new Date()
    return pedidosValidos.value.filter(pedido => {
      const data = new Date(pedido.data_criacao)
      return data.getFullYear() === hoje.getFullYear() && data.getMonth() === hoje.getMonth()
    })
  })

  const vendasDoMes = computed(() => {
    let total = 0
    for (const pedido of pedidosDoMes.value) {
      total += Number(pedido.valor_liquido || 0)
    }
    return total
  })

  const ticketMedio = computed(() => {
    if (pedidosDoMes.value.length === 0) return 0
    return vendasDoMes.value / pedidosDoMes.value.length
  })

  const vendasUltimosDias = computed(() => {
    const dias = []
    for (let i = DIAS_GRAFICO - 1; i >= 0; i--) {
      const data = new Date()
      data.setDate(data.getDate() - i)
      const chave = chaveDoDia(data)

      let valor = 0
      for (const pedido of pedidosValidos.value) {
        if (chaveDoDia(new Date(pedido.data_criacao)) === chave) {
          valor += Number(pedido.valor_liquido || 0)
        }
      }

      dias.push({
        chave: chave,
        rotulo: data.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', ''),
        detalhe: data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }),
        valor: valor,
      })
    }
    return dias
  })

  const produtosMaisVendidos = computed(() => {
    const porProduto = {}
    for (const pedido of pedidosValidos.value) {
      for (const item of pedido.itens) {
        const chave = item.produto || `removido:${item.nome_produto}`
        if (!porProduto[chave]) {
          porProduto[chave] = { chave: chave, produto: item.produto, nome: item.nome_produto, quantidade: 0, total: 0 }
        }
        porProduto[chave].quantidade += Number(item.quantidade || 0)
        porProduto[chave].total += Number(item.subtotal || 0)
      }
    }
    return Object.values(porProduto)
      .sort((a, b) => b.quantidade - a.quantidade || b.total - a.total)
      .slice(0, LIMITE_MAIS_VENDIDOS)
  })

  async function carregar() {
    carregando.value = true
    erro.value = ''
    try {
      loja.value = await api.lojas.eu()
      semLoja.value = false
      const [produtosRecebidos, pedidosRecebidos, statusRecebidos, categoriasRecebidas] = await Promise.all([
        api.produtos.listarMeus(),
        api.pedidos.listarMinhaLoja(),
        api.pedidos.listarStatusDisponiveis(),
        api.categorias.listar(),
      ])
      produtos.value = produtosRecebidos
      pedidos.value = pedidosRecebidos
      categorias.value = categoriasRecebidas
      const ids = {}
      for (const item of statusRecebidos) {
        ids[item.status] = item.status_pedido_id
      }
      statusIds.value = ids
      carregado.value = true
    } catch (falha) {
      if (falha?.status === 404) {
        limpar()
        semLoja.value = true
        carregado.value = true
      } else {
        erro.value = falha?.data?.detail || 'Não foi possível carregar a área do produtor.'
      }
    } finally {
      carregando.value = false
    }
  }

  async function atualizarStatus(pedido, novoStatus) {
    const statusId = statusIds.value[novoStatus]
    if (!statusId) throw new Error('O status necessário ainda não está disponível.')

    try {
      const atualizado = await api.pedidos.atualizarStatus(pedido.pedido_id, statusId)
      pedidos.value = pedidos.value.map(item => item.pedido_id === atualizado.pedido_id ? atualizado : item)
    } catch (falha) {
      throw new Error(extrairMensagemErro(falha))
    }

    if (novoStatus === 'Cancelado') await recarregarProdutos()
  }

  async function salvarProduto({ dados, precoVenda, precoCusto, desconto, imagens, produtoExistente }) {
    let produtoId
    try {
      if (produtoExistente) {
        produtoId = produtoExistente.produto_id
        await api.produtos.atualizar(produtoId, dados)
      } else {
        const criado = await api.produtos.criar(dados)
        produtoId = criado.produto_id
      }

      const novoPreco = montarNovoPreco(produtoId, { precoVenda, precoCusto, desconto }, produtoExistente)
      if (novoPreco) await api.produtos.criarPreco(novoPreco)
    } catch (falha) {
      throw new Error(extrairMensagemErro(falha))
    }

    const erroImagem = imagens ? await sincronizarImagens(produtoId, imagens, produtoExistente?.imagens || []) : ''

    await recarregarProdutos()
    return { erroImagem }
  }

  async function sincronizarImagens(produtoId, { itens, chavePrincipal, removidas }, imagensAtuais) {
    const falhas = []
    const idsPorChave = {}

    for (const imagemId of removidas) {
      try {
        await api.produtos.removerImagem(produtoId, imagemId)
      } catch (falha) {
        falhas.push(extrairMensagemErro(falha))
      }
    }

    for (const item of itens) {
      if (item.id) {
        idsPorChave[item.chave] = item.id
        continue
      }
      try {
        const enviada = await api.produtos.enviarImagem(produtoId, item.arquivo, item.chave === chavePrincipal)
        idsPorChave[item.chave] = enviada.id
      } catch (falha) {
        falhas.push(`${item.arquivo.name}: ${extrairMensagemErro(falha)}`)
      }
    }

    const principalAtual = imagensAtuais.find(imagem => imagem.e_principal)?.id
    const itemPrincipal = itens.find(item => item.chave === chavePrincipal)
    if (itemPrincipal?.id && itemPrincipal.id !== principalAtual) {
      try {
        await api.produtos.definirImagemPrincipal(produtoId, itemPrincipal.id)
      } catch (falha) {
        falhas.push(extrairMensagemErro(falha))
      }
    }

    const ordemDesejada = itens.map(item => idsPorChave[item.chave]).filter(Boolean)
    const ordemResultante = [
      ...imagensAtuais.map(imagem => imagem.id).filter(id => ordemDesejada.includes(id)),
      ...itens.filter(item => !item.id).map(item => idsPorChave[item.chave]).filter(Boolean),
    ]
    if (!falhas.length && ordemDesejada.join() !== ordemResultante.join()) {
      try {
        await api.produtos.reordenarImagens(produtoId, ordemDesejada)
      } catch (falha) {
        falhas.push(extrairMensagemErro(falha))
      }
    }

    return falhas.join(' ')
  }

  async function alternarAtivo(produto) {
    try {
      const atualizado = await api.produtos.atualizar(produto.produto_id, { ativo: !produto.ativo })
      produtos.value = produtos.value.map(item => item.produto_id === atualizado.produto_id ? atualizado : item)
      return atualizado
    } catch (falha) {
      throw new Error(extrairMensagemErro(falha))
    }
  }

  async function salvarLoja(campos) {
    try {
      loja.value = await api.lojas.atualizarMinha(campos)
      return loja.value
    } catch (falha) {
      const erroDaApi = new Error(extrairMensagemErro(falha))
      erroDaApi.campos = falha?.data || {}
      throw erroDaApi
    }
  }

  async function salvarImagemLoja(arquivo) {
    const atualizada = await api.lojas.atualizarImagem(arquivo)
    loja.value = { ...loja.value, imagem_perfil: atualizada.imagem_perfil || null }
    return loja.value
  }

  async function removerImagemLoja() {
    try {
      await api.lojas.removerImagem()
    } catch (falha) {
      if (falha.status !== 404) throw falha
    }
    loja.value = { ...loja.value, imagem_perfil: null }
    return loja.value
  }

  async function recarregarProdutos() {
    try {
      produtos.value = await api.produtos.listarMeus()
    } catch (falha) {
      console.error(falha)
    }
  }

  function limpar() {
    loja.value = null
    semLoja.value = false
    produtos.value = []
    pedidos.value = []
    categorias.value = []
    statusIds.value = {}
    carregado.value = false
    erro.value = ''
  }

  return {
    loja, semLoja, produtos, pedidos, categorias, carregando, carregado, erro,
    produtosAtivos, produtosInativos, pedidosPorStatus, quantidadePendentes, quantidadeEmAndamento,
    pedidosDoMes, vendasDoMes, ticketMedio, vendasUltimosDias, produtosMaisVendidos,
    carregar, atualizarStatus, salvarProduto, alternarAtivo, salvarLoja, salvarImagemLoja, removerImagemLoja, limpar,
  }
})

function chaveDoDia(data) {
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${data.getFullYear()}-${mes}-${dia}`
}

function valorOuNulo(valor) {
  const texto = campoParaDecimal(valor)
  return texto === '' ? null : texto
}

function mesmoValor(informado, atual) {
  const normalizar = valor => (valor === null || valor === undefined ? null : Number(valor))
  return normalizar(informado) === normalizar(atual)
}

function montarNovoPreco(produtoId, { precoVenda, precoCusto, desconto }, produtoExistente) {
  const novoPreco = {
    produto: produtoId,
    preco_venda: campoParaDecimal(precoVenda),
    preco_custo: valorOuNulo(precoCusto),
    porcentagem_desconto: Number(desconto) || 0,
  }
  if (!produtoExistente) return novoPreco

  const mudou = !mesmoValor(novoPreco.preco_venda, produtoExistente.preco_venda)
    || !mesmoValor(novoPreco.preco_custo, produtoExistente.preco_custo)
    || novoPreco.porcentagem_desconto !== (Number(produtoExistente.porcentagem_desconto) || 0)
  return mudou ? novoPreco : null
}
