export interface CepAddress { street: string; district: string; city: string; state: string }

export async function lookupCep(value: string): Promise<CepAddress> {
  const cep = value.replace(/\D/g, '')
  if (cep.length !== 8) throw new Error('Digite um CEP com 8 números.')
  const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`)
  if (!response.ok) throw new Error('Não foi possível consultar o CEP.')
  const body = await response.json() as { erro?: boolean; logradouro?: string; bairro?: string; localidade?: string; uf?: string }
  if (body.erro) throw new Error('CEP não encontrado.')
  return { street: body.logradouro ?? '', district: body.bairro ?? '', city: body.localidade ?? '', state: body.uf ?? '' }
}
