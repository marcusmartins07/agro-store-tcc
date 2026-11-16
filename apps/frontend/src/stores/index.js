import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/services/api.js'

export const useCarrinhoStore = defineStore('carrinho', () => {
  const carrinhos = ref([])
  const carregando = ref(false)
  const erro = ref('')

  const itens = computed(() => {
    const lista = []
    for (const carrinho of carrinhos.value) {
      for (const item of carrinho.itens) {
        lista.push({
          ...item,
          carrinho_id: carrinho.carrinho_id,
          loja: carrinho.loja,
          loja_nome: carrinho.loja_nome,
        })
      }
    }
    return lista
  })

  const totalItens = computed(() => {
    let total = 0
    for (const item of itens.value) {
      total += Number(item.quantidade || 0)
    }
    return total
  })

  const porFornecedor = computed(() => {
    const grupos = {}
    for (const item of itens.value) {
      const fornecedor = item.loja_nome || 'Fornecedor'
      if (!grupos[fornecedor]) grupos[fornecedor] = []
      grupos[fornecedor].push(item)
    }
    return grupos
  })

  async function carregar() {
    if (!localStorage.getItem('access_token')) {
      limparLocal()
      return
    }

    carregando.value = true
    erro.value = ''
    try {
      carrinhos.value = await api.carrinhos.listar()
    } catch (e) {
      erro.value = extrairMensagemErro(e)
      throw e
    } finally {
      carregando.value = false
    }
  }

  async function adicionar(produtoId, quantidade = 1) {
    erro.value = ''
    try {
      await api.carrinhos.adicionar(produtoId, quantidade)
      await carregar()
    } catch (e) {
      erro.value = extrairMensagemErro(e)
      throw e
    }
  }

  async function alterarQuantidade(itemId, quantidade) {
    erro.value = ''
    try {
      await api.carrinhos.atualizarItem(itemId, quantidade)
      await carregar()
    } catch (e) {
      await recarregarAposFalha(e)
      throw e
    }
  }

  async function remover(itemId) {
    erro.value = ''
    try {
      await api.carrinhos.removerItem(itemId)
      await carregar()
    } catch (e) {
      erro.value = extrairMensagemErro(e)
      throw e
    }
  }

  async function finalizar(carrinhoProdutoIds) {
    erro.value = ''
    try {
      const pedidos = await api.pedidos.finalizarCarrinho(carrinhoProdutoIds)
      await carregar()
      return pedidos
    } catch (e) {
      await recarregarAposFalha(e)
      throw e
    }
  }

  async function recarregarAposFalha(falha) {
    const mensagem = extrairMensagemErro(falha)
    try {
      await carregar()
    } catch (e) {
      console.error(e)
    }
    erro.value = mensagem
  }

  function limparLocal() {
    carrinhos.value = []
    erro.value = ''
  }

  return {
    carregando,
    erro,
    itens,
    porFornecedor,
    totalItens,
    carregar,
    adicionar,
    alterarQuantidade,
    remover,
    finalizar,
    limparLocal,
  }
})

export const useFavoritosStore = defineStore('favoritos', () => {
  const itens = ref([])
  const carregando = ref(false)
  const carregado = ref(false)
  const erro = ref('')
  const produtosEmOperacao = ref([])

  const ordenados = computed(() =>
    [...itens.value].sort((a, b) => new Date(b.data_criacao) - new Date(a.data_criacao))
  )

  function favoritoDoProduto(produtoId) {
    return itens.value.find(item => item.produto === produtoId)
  }

  function isFavorito(produtoId) {
    return Boolean(favoritoDoProduto(produtoId))
  }

  function isOperando(produtoId) {
    return produtosEmOperacao.value.includes(produtoId)
  }

  function definirOperacao(produtoId, emOperacao) {
    if (emOperacao) {
      produtosEmOperacao.value.push(produtoId)
    } else {
      produtosEmOperacao.value = produtosEmOperacao.value.filter(id => id !== produtoId)
    }
  }

  async function carregar(forcar = false) {
    if (!localStorage.getItem('access_token')) {
      limparLocal()
      return
    }
    if (carregando.value || (carregado.value && !forcar)) return

    carregando.value = true
    erro.value = ''
    try {
      itens.value = await api.favoritos.listar()
      carregado.value = true
    } catch (e) {
      erro.value = extrairMensagemErro(e)
      throw e
    } finally {
      carregando.value = false
    }
  }

  async function adicionar(produtoId) {
    if (isOperando(produtoId)) return

    definirOperacao(produtoId, true)
    erro.value = ''
    try {
      const favorito = await api.favoritos.adicionar(produtoId)
      itens.value.unshift(favorito)
      carregado.value = true
    } catch (e) {
      erro.value = extrairMensagemErro(e)
      throw e
    } finally {
      definirOperacao(produtoId, false)
    }
  }

  async function remover(produtoId) {
    const favorito = favoritoDoProduto(produtoId)
    if (!favorito || isOperando(produtoId)) return

    definirOperacao(produtoId, true)
    erro.value = ''
    try {
      await api.favoritos.remover(favorito.favorito_id)
      itens.value = itens.value.filter(item => item.favorito_id !== favorito.favorito_id)
    } catch (e) {
      erro.value = extrairMensagemErro(e)
      throw e
    } finally {
      definirOperacao(produtoId, false)
    }
  }

  async function alternar(produtoId) {
    if (isFavorito(produtoId)) await remover(produtoId)
    else await adicionar(produtoId)
  }

  function limparLocal() {
    itens.value = []
    carregando.value = false
    carregado.value = false
    erro.value = ''
    produtosEmOperacao.value = []
  }

  return {
    itens,
    carregando,
    erro,
    ordenados,
    isFavorito,
    isOperando,
    carregar,
    alternar,
    limparLocal,
  }
})

export function extrairMensagemErro(error) {
  if (!error || !error.data) return 'Não foi possível concluir a operação.'
  if (error.data.detail) return error.data.detail

  const primeiroCampo = Object.keys(error.data)[0]
  if (primeiroCampo) {
    const valor = error.data[primeiroCampo]
    if (Array.isArray(valor)) return valor[0]
    return String(valor)
  }

  return 'Não foi possível concluir a operação.'
}
