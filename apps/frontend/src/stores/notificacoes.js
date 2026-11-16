import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotificacoesStore = defineStore('notificacoes', () => {
  const notificacoes = ref([])
  let proximoId = 1

  function notificar(dados) {
    const id = proximoId
    proximoId++
    notificacoes.value.push({ id: id, tipo: dados.tipo || 'info', mensagem: dados.mensagem })

    if (dados.tempo) {
      setTimeout(() => remover(id), dados.tempo * 1000)
    }
  }

  function remover(id) {
    notificacoes.value = notificacoes.value.filter(notificacao => notificacao.id !== id)
  }

  return { notificacoes, notificar, remover }
})
