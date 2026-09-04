# Painel Comercial SEIBT

Painel de pedidos e faturamento que a diretoria e os gestores abrem pelo
celular ou pelo computador, sem instalar nada.

## Como funciona, em uma frase

Um programa roda aqui dentro da empresa, busca os números no sistema e envia
para o GitHub. O painel publicado lê esses números e se atualiza sozinho.

## O que tem em cada pasta

| Pasta | Para que serve |
|---|---|
| `docs/` | O painel em si. É o que vai para o GitHub e o que as pessoas abrem. |
| `atualizar/` | O programa que busca os números. Fica só na máquina da empresa. |
| `testes/` | Confere se está tudo certo. Rode antes de publicar mudanças. |

## Antes de publicar

Abra o Prompt de Comando nesta pasta e rode:

```
python testes\testar.py
```

Tem que terminar com "TODOS OS TESTES PASSARAM".

## Manter os números atualizados

O arquivo `atualizar\atualizar.bat` busca os números e envia para o GitHub.
Para ele rodar sozinho de tempo em tempo, agende no Agendador de Tarefas do
Windows (passo a passo abaixo).

### Agendar

1. Menu Iniciar, procure **Agendador de Tarefas** e abra
2. No menu à direita, clique em **Criar Tarefa** (não é "Tarefa Básica")
3. Aba **Geral**: dê o nome `Atualizar Painel SEIBT` e marque
   **Executar estando o usuário conectado ou não**
4. Aba **Disparadores**, botão **Novo**: escolha **Diariamente**, marque
   **Repetir a cada: 30 minutos**, com duração **Indefinidamente**
5. Aba **Ações**, botão **Novo**: em Programa, aponte para o
   `atualizar\atualizar.bat` desta pasta
6. Aba **Condições**: desmarque **Iniciar a tarefa somente se o computador
   estiver na energia** (senão não roda no notebook na bateria)
7. Clique OK

### Se os números pararem de atualizar

O próprio painel avisa na tela quando os números estão parados há mais de
30 minutos. Se isso aparecer, rode o `atualizar\atualizar.bat` na mão e leia
a mensagem que aparecer na janela.

## Trocar meta ou ponto de equilíbrio

Estão no começo do arquivo `docs\app.js`, com os nomes `META_ANUAL` e
`PE_MENSAL`. Depois de mudar, rode os testes e envie para o GitHub.
