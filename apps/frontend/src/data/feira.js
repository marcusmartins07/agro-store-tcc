export const feira = {
  diaSemana: 'Sábado',
  horarioInicio: '6h',
  horarioFim: '12h',
  endereco: 'Rua Major Lúcio Meireles, nº 61 — Centro, Camaquã',
}

export function textoRetirada() {
  return `Retirada aos ${feira.diaSemana.toLowerCase()}s, das ${feira.horarioInicio} às ${feira.horarioFim}, em ${feira.endereco}.`
}
