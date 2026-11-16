const API_BASE_URL = '/api/v1'

async function refreshAccessToken() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) throw new Error('Sem refresh token')

  const response = await fetch(`${API_BASE_URL}/usuarios/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })

  if (!response.ok) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
    throw new Error('Sessão expirada')
  }

  const dados = await response.json()
  localStorage.setItem('access_token', dados.access)
  return dados.access
}

// autenticar: false não envia o JWT (endpoints públicos que não devem depender da sessão salva)
async function request(endpoint, options = {}, retry = true, autenticar = true) {
  const token = autenticar ? localStorage.getItem('access_token') : null
  const headers = {}

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) headers.Authorization = `Bearer ${token}`

  let response = await fetch(`${API_BASE_URL}${endpoint}`, { method: options.method, body: options.body, headers: headers })

  if (response.status === 401 && retry) {
    const novoToken = await refreshAccessToken()
    headers.Authorization = `Bearer ${novoToken}`
    response = await fetch(`${API_BASE_URL}${endpoint}`, { method: options.method, body: options.body, headers: headers })
  }

  if (!response.ok) {
    const erro = await response.json().catch(() => ({}))
    throw { status: response.status, data: erro }
  }

  if (response.status === 204) return null
  return response.json()
}

export const api = {
  produtos: {
    listar: () => request('/produtos/'),
    obter: (produtoId) => request(`/produtos/${produtoId}/`),
    listarMeus: () => request('/produtos/meus/'),
    criar: (body) => request('/produtos/', { method: 'POST', body: JSON.stringify(body) }),
    atualizar: (produtoId, body) => request(`/produtos/${produtoId}/`, { method: 'PATCH', body: JSON.stringify(body) }),
    enviarImagem: (produtoId, arquivo, ePrincipal = false) => {
      const formData = new FormData()
      formData.append('imagem', arquivo)
      if (ePrincipal) formData.append('e_principal', 'true')
      return request(`/produtos/${produtoId}/imagens/`, { method: 'POST', body: formData })
    },
    definirImagemPrincipal: (produtoId, imagemId) => request(`/produtos/${produtoId}/imagens/${imagemId}/`, {
      method: 'PATCH',
      body: JSON.stringify({ e_principal: true }),
    }),
    removerImagem: (produtoId, imagemId) => request(`/produtos/${produtoId}/imagens/${imagemId}/`, { method: 'DELETE' }),
    reordenarImagens: (produtoId, imagemIds) => request(`/produtos/${produtoId}/imagens/reordenar/`, {
      method: 'POST',
      body: JSON.stringify({ imagens: imagemIds }),
    }),
    criarPreco: (body) => request('/produtos/precos/', { method: 'POST', body: JSON.stringify(body) }),
  },
  categorias: {
    listar: () => request('/produtos/categorias/?ativo=true'),
  },
  auth: {
    login: (cpf, password) => request('/usuarios/login/', { method: 'POST', body: JSON.stringify({ cpf, password }) }, false),
    cadastrar: (body) => request('/usuarios/cadastro/', { method: 'POST', body: JSON.stringify(body) }, false),
    solicitarRedefinicaoSenha: (email) => request('/usuarios/redefinir-senha/', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }, false, false),
    confirmarRedefinicaoSenha: ({ token, password, password_confirmacao }) => request('/usuarios/redefinir-senha/confirmar/', {
      method: 'POST',
      body: JSON.stringify({ token, password, password_confirmacao }),
    }, false, false),
  },
  usuarios: {
    eu: () => request('/usuarios/eu/'),
    atualizar: (body) => request('/usuarios/eu/', { method: 'PATCH', body: JSON.stringify(body) }),
    atualizarFoto: (arquivo) => {
      const formData = new FormData()
      formData.append('foto_perfil', arquivo)
      return request('/usuarios/eu/', { method: 'PATCH', body: formData })
    },
    removerFoto: () => request('/usuarios/eu/foto/', { method: 'DELETE' }),
  },
  tiposTelefone: {
    listar: () => request('/tipos-telefone/', {}, false, false),
  },
  generos: {
    listar: () => request('/generos/', {}, false, false),
  },
  telefones: {
    listar: () => request('/usuarios/eu/telefones/'),
    criar: (body) => request('/usuarios/eu/telefones/', { method: 'POST', body: JSON.stringify(body) }),
    atualizar: (telefoneId, body) => request(`/usuarios/eu/telefones/${telefoneId}/`, { method: 'PATCH', body: JSON.stringify(body) }),
    excluir: (telefoneId) => request(`/usuarios/eu/telefones/${telefoneId}/`, { method: 'DELETE' }),
  },
  lojas: {
    // Com imagem, a criação vai em multipart (o navegador define o Content-Type); sem imagem, continua em JSON
    criar: (body, imagem = null) => {
      if (!imagem) {
        return request('/lojas/lojas/', { method: 'POST', body: JSON.stringify(body) })
      }
      const formData = new FormData()
      for (const campo of Object.keys(body)) {
        const valor = body[campo]
        if (valor !== undefined && valor !== null && valor !== '') {
          formData.append(campo, valor)
        }
      }
      formData.append('imagem_perfil', imagem)
      return request('/lojas/lojas/', { method: 'POST', body: formData })
    },
    obter: (lojaId) => request(`/lojas/lojas/${lojaId}/`, {}, false, false),
    eu: () => request('/lojas/eu/'),
    atualizarMinha: (body) => request('/lojas/eu/', { method: 'PATCH', body: JSON.stringify(body) }),
    atualizarImagem: (arquivo) => {
      const formData = new FormData()
      formData.append('imagem_perfil', arquivo)
      return request('/lojas/eu/', { method: 'PATCH', body: formData })
    },
    removerImagem: () => request('/lojas/eu/imagem/', { method: 'DELETE' }),
  },
  carrinhos: {
    listar: () => request('/carrinhos/'),
    adicionar: (produto, quantidade = 1) => request('/carrinhos/', {
      method: 'POST',
      body: JSON.stringify({ produto, quantidade }),
    }),
    atualizarItem: (itemId, quantidade) => request(`/carrinhos/itens/${itemId}/`, {
      method: 'PATCH',
      body: JSON.stringify({ quantidade }),
    }),
    removerItem: (itemId) => request(`/carrinhos/itens/${itemId}/`, { method: 'DELETE' }),
  },
  avaliacoes: {
    listarPorProduto: (produtoId) => request(`/avaliacoes/?produto=${encodeURIComponent(produtoId)}`),
    criar: (body) => request('/avaliacoes/', { method: 'POST', body: JSON.stringify(body) }),
  },
  favoritos: {
    listar: () => request('/favoritos/'),
    adicionar: (produto) => request('/favoritos/', { method: 'POST', body: JSON.stringify({ produto }) }),
    remover: (favoritoId) => request(`/favoritos/${favoritoId}/`, { method: 'DELETE' }),
  },
  pedidos: {
    listar: () => request('/pedidos/'),
    finalizarCarrinho: (carrinhoProdutoIds) => request('/pedidos/', {
      method: 'POST',
      body: JSON.stringify({ carrinho_produto_ids: carrinhoProdutoIds }),
    }),
    listarMinhaLoja: () => request('/pedidos/minha-loja/'),
    listarStatusDisponiveis: () => request('/pedidos/status-disponiveis/'),
    atualizarStatus: (pedidoId, status) => request(`/pedidos/${pedidoId}/status/`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
    cancelar: (pedidoId) => request(`/pedidos/${pedidoId}/cancelar/`, { method: 'PATCH' }),
    confirmarEntrega: (pedidoId) => request(`/pedidos/${pedidoId}/confirmar-entrega/`, { method: 'PATCH' }),
  },
}
