🍕 Planejamento: Sistema de Controle de Estoque - Palhete Pizzaria
1. Arquitetura do Sistema (Requisitos Não Funcionais)
Hospedagem Local: O sistema rodará localmente no computador principal da pizzaria a partir de um executável.

Acesso Mobile: A interface de uso será web/responsiva, acessada pelos navegadores dos celulares dos funcionários conectados à mesma rede Wi-Fi.

Leitura de Código de Barras: A captura dos códigos será feita através da câmera dos celulares que estão acessando o sistema.

2. Requisitos Funcionais (O que o sistema faz)
RF01 - Identificação: Permitir a leitura do código de barras usando a câmera do celular para identificar produtos.

RF02 - Primeiro Cadastro: Vincular um código de barras inédito a um nome de produto existente na base de dados.

RF03 - Entrada de Lotes: Registrar a entrada de mercadorias solicitando a quantidade total e a data de validade, criando um novo lote.

RF04 - Saída Orientada (PEPS): Exibir a quantidade total disponível de um produto e um alerta visual destacando a data de validade do lote mais antigo que deve ser consumido primeiro.

RF05 - Baixa Inteligente: Descontar a quantidade retirada automaticamente do lote com a validade mais próxima. Se o lote zerar, a baixa continua no próximo lote disponível.

RF06 - Estorno/Devolução: Permitir que o funcionário acesse suas últimas retiradas e desfaça uma ação, devolvendo a quantidade exata para o lote original de onde o produto saiu.

RF07 - Estoque Mínimo: Permitir a configuração de uma quantidade mínima de segurança (alerta) para cada produto.

RF08 - Dashboard de Alertas: Exibir no painel principal os produtos abaixo do estoque mínimo e os produtos próximos ao vencimento.

RF09 - Exportação de Compras (Novo): Gerar um arquivo .csv (planilha) contendo a lista de produtos que estão abaixo do estoque mínimo, para ser enviado à responsável pelas compras.

3. Regras de Negócio (As leis do sistema)
RN01: O controle foca apenas no Estoque Central (sem subdivisões de setores como salão ou cozinha).

RN02: O código de barras atua apenas como chave de busca do produto; informações dinâmicas (validade e quantidade) pertencem ao Lote.

RN03: Todas as movimentações (Entrada, Saída e Devolução) devem registrar o nome/ID do funcionário responsável pela ação.

4. Estrutura do Banco de Dados
O banco será composto por 5 tabelas relacionais:

Usuario: id, nome, pin_acesso (senha numérica simples).

Produto: id, nome, estoque_minimo, unidade_medida.

Codigo_Barras: codigo (chave primária lida pela câmera), produto_id.

Lote_Estoque: id, produto_id, quantidade_inicial, quantidade_atual, data_validade, data_entrada.

Movimentacao: id, lote_id, usuario_id, tipo_movimentacao (Entrada, Saída, Devolução), quantidade, data_hora.

5. Cenários de Teste Principais
CT01 - Retirada Simples: Funcionário retira uma quantidade menor ou igual ao disponível no lote mais antigo. O sistema debita apenas desse lote e registra a saída.

CT02 - Quebra de Lote (Teste PEPS): Funcionário retira uma quantidade maior do que a disponível no lote mais antigo. O sistema zera o lote antigo e debita o restante da quantidade do próximo lote, registrando a operação.

CT03 - Estoque Insuficiente: Funcionário tenta retirar mais itens do que a soma de todos os lotes disponíveis. O sistema bloqueia a ação e exibe alerta de erro.

CT04 - Devolução de Retirada: Funcionário acessa o histórico e devolve 1 unidade recém-retirada. O sistema soma 1 unidade de volta à quantidade_atual do lote exato de onde o item saiu, registrando o tipo de movimentação como "Devolução".