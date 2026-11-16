# Agro Store - Guia técnico de execução

Este guia explica, passo a passo, como baixar e executar o Agro Store com o banco de demonstração já carregado. Foi escrito para quem nunca usou Docker. A documentação completa (API, regras de negócio e detalhes) está no [README.md](README.md).

## 1. Resumo do projeto

O Agro Store é um MVP desenvolvido como Trabalho de Conclusão de Curso: uma plataforma web para compra e venda de produtos rurais, voltada à Feira do Produtor Rural Willi Dummer, em Camaquã/RS. A retirada dos pedidos é presencial na feira; o MVP não tem pagamento online, entrega nem frete.

### Funcionalidades principais

- Catálogo público de produtos, com filtro por categoria e imagens por produto.
- Cadastro de clientes, login com JWT, perfil, telefones e foto de perfil.
- Redefinição de senha por e-mail.
- Favoritos e carrinho salvo no backend.
- Finalização do carrinho, com um pedido por loja e baixa de estoque.
- Cancelamento de pedidos pendentes e confirmação de recebimento pelo cliente.
- Avaliação de produtos comprados.
- Área do produtor: indicadores, pedidos, produtos, preços, imagens e dados da loja.

### Arquitetura

Monorepo executado inteiramente com Docker Compose, em três serviços:

| Serviço | Tecnologia | Endereço no computador |
| --- | --- | --- |
| `frontend` | Vue 3 + Vite + Bootstrap | http://localhost:5173 |
| `backend` | Django + Django REST Framework + JWT | http://localhost:8000 |
| `db` | PostgreSQL 17.11 | 127.0.0.1:5433 |

A comunicação entre frontend e backend é feita por API REST em JSON.


## 2. Pré-requisitos

Você não precisa instalar Python, Node.js nem PostgreSQL. Tudo isso roda dentro dos containers Docker.

### O que instalar

- **Git**, para baixar o projeto: https://git-scm.com/downloads
- **Docker com Compose v2**. O `docker-compose.yml` usa `env_file` com `required: false`, que exige **Docker Compose 2.24 ou superior**. Para conferir a versão:

```bash
docker compose version
```

### Por sistema operacional

- **Windows**: instale o Docker Desktop com o backend WSL 2 (o instalador oferece essa opção). Abra o Docker Desktop e aguarde o status "Engine running" antes de continuar.
- **macOS**: instale o Docker Desktop (versão para chip Apple ou Intel, conforme o seu Mac) e abra o aplicativo.
- **Linux**: instale o Docker Engine e o plugin Compose (`docker-compose-plugin`), seguindo https://docs.docker.com/engine/install/. Use `sudo` antes dos comandos `docker` ou adicione seu usuário ao grupo `docker` (veja a seção 6).

### Portas e recursos

- Portas livres no computador, todas ligadas somente a `127.0.0.1`: **5173** (frontend), **8000** (backend) e **5433** (banco).
- Espaço em disco: reserve cerca de 2 GB (as imagens Docker do projeto somam aproximadamente 1,5 GB).
- Internet na primeira execução, para baixar as imagens e as dependências.

## 3. Passo a passo para rodar

1. Baixe o projeto e entre na pasta:

```bash
git clone https://github.com/marcusmartins07/agro-store.git
cd agro-store
```

2. Abra o Docker Desktop (Windows e macOS) e espere ele terminar de iniciar. No Linux, confirme que o serviço do Docker está ativo.

3. Na raiz do repositório, suba o sistema:

```bash
docker compose up --build
```

4. Aguarde. A primeira subida baixa as imagens e instala as dependências, então leva alguns minutos; as seguintes são bem mais rápidas.

### O que esperar nos logs

- O serviço `db` carrega o arquivo `01-dados-demo.sql` na primeira execução (somente com o banco vazio).
- O serviço `backend` só inicia depois que o banco está saudável e mostra mensagens como `No migrations to apply` e `Starting development server`.
- O serviço `frontend` inicia o servidor do Vite.

Quando essas mensagens aparecerem, o sistema está pronto. Deixe esse terminal aberto.

### Endereços de acesso

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1/
- Administração do Django: http://localhost:8000/admin/

### Criar o administrador

O banco de demonstração não traz conta de administrador. Ela é necessária, por exemplo, para habilitar produtores. Em **outro terminal**, na raiz do repositório:

```bash
docker compose exec backend python manage.py createsuperuser
```

Siga as perguntas do terminal para definir o acesso.

### Contas de demonstração

O banco traz contas de produtor e de cliente para testar o sistema. Para entrar no sistema (em http://localhost:5173), informe o CPF da conta (somente números ou com pontos e traço) e a senha. A senha padrão, igual para todas as contas abaixo, é `Senha@123`.

| Nome | CPF | Perfil |
| --- | --- | --- |
| Juliana Bitencourt | 12345678899 | Produtor |
| Gustavo Dias | 12345678900 | Cliente |
| Vinicius Silva | 12345678901 | Produtor |
| Leonardo Moraes | 12345678301 | Produtor |
| Marcus Martins | 26675972065 | Cliente |
| Rodrigo Alves | 04037001080 | Cliente |
| Livia Pereira | 05235104030 | Cliente |
| Patrícia Centeno | 80427489067 | Cliente |
| Fulano da Silva | 67245132003 | Cliente |
| Eduarda Fagundes | 52998224725 | Produtor |
| Fernanda Lemos | 11144477735 | Cliente |
| QA Produtor Teste | 87991126714 | Produtor |
| QA Cliente Editado | 67151312440 | Cliente |

Essas credenciais valem apenas para o ambiente local de demonstração.

### O que já vem carregado

O banco de demonstração inclui, aproximadamente, 5 lojas, mais de 20 produtos com fotos, além de pedidos, avaliações e favoritos de exemplo.

## 4. Uso do dia a dia

Todos os comandos na raiz do repositório.

| Ação | Comando |
| --- | --- |
| Parar (no terminal onde está rodando) | `Ctrl+C` |
| Parar e remover os containers, preservando os dados | `docker compose down` |
| Subir de novo | `docker compose up` |
| Subir em segundo plano | `docker compose up -d` |
| Acompanhar os logs em segundo plano | `docker compose logs -f` |
| Rodar os testes do backend | `docker compose exec backend python manage.py test --noinput agrostore` |

O comando `docker compose down` mantém o banco: ao subir de novo, os dados continuam. Use `--build` no `up` quando as dependências mudarem (`apps/backend/requirements.txt` ou `apps/frontend/package.json`).

## 5. Recarregar o banco de demonstração do zero

A carga de demonstração só acontece quando o volume do banco está vazio. Se você já subiu o sistema antes, o banco existente é mantido e a carga não é refeita. Para voltar ao estado inicial:

1. Pare o sistema e apague o banco local (isso remove todos os dados do banco, inclusive o administrador criado):

```bash
docker compose down -v
```

2. Apague a pasta `apps/backend/media/` para recarregar também as imagens. O backend só copia as imagens de demonstração quando essa pasta não tem nenhum arquivo.

3. Suba de novo:

```bash
docker compose up --build
```

## 6. Solução de problemas

- **Porta em uso** (erro como "port is already allocated"): outro programa usa a 5173, 8000 ou 5433. Feche-o e rode `docker compose up` novamente.
- **Docker não iniciado** (erro como "cannot connect to the Docker daemon" ou "error during connect"): abra o Docker Desktop e aguarde terminar de iniciar; no Linux, inicie o serviço do Docker.
- **Banco sem dados de demonstração**: o volume do banco já existia, e a carga só ocorre com o volume vazio. Siga a seção 5.
- **Carga falhou no meio**: a próxima subida não repete a carga. Rode `docker compose down -v` e suba de novo.
- **Imagens dos produtos não aparecem**: a pasta `apps/backend/media/` provavelmente já tinha arquivos e a cópia não foi feita. Apague `apps/backend/media/` e suba novamente (seção 5).
- **Linux com "permission denied" no Docker**: execute os comandos com `sudo` ou adicione seu usuário ao grupo `docker` com `sudo usermod -aG docker $USER` e abra uma nova sessão. Se a pasta `apps/backend/media/` foi criada pelo container e não puder ser apagada, use `sudo rm -rf apps/backend/media`.
