# PROGRESS.md - Socratic CT-Tutor

## Status Atual
- **Fase**: 4 - Avaliação Psicométrica com DeepEval e Análise para o Artigo
- **Estado**: Em andamento
- **Data de Início**: 2025-07-25
- **Data de Conclusão Fase 1**: 2025-07-25
- **Data de Conclusão Fase 2**: 2025-07-25
- **Data de Conclusão Fase 3**: 2026-07-30

## Histórico de Modificações

### 2025-07-25 - Início da Fase 1
- Análise completa do codebase (`nodes.py`, `workflow.py`, `prompts.py`, `api.py`, `dashboard.py`)
- Identificação dos problemas arquiteturais listados no AGENTS.md Seção 2
- Criação do plano de execução incremental

### 2025-07-25 - Conclusão da Fase 1 (Parte 1)
- Criado `llm_factory.py` com factory centralizada do LLM (max_retries=3, timeout=30s)
- Criado `message_utils.py` com `get_last_human_message()` e `get_last_ai_message()`
- Migrados 10 prompts inline de `nodes.py` para `prompts.py`
- Eliminado `.replace("_node", "")` do `intent_router` (linha 88 original)
- Substituídos loops duplicados por chamadas às funções utilitárias
- Todos os nós de tutoria usam prompts importados de `prompts.py`
- Reset de `approved` e `evaluation_feedback` padronizado em todos os nós

### 2025-07-25 - Conclusão da Fase 1 (Parte 2 - Nó de Síntese)
- Adicionado `FINAL_SUMMARY_NODE_PROMPT` em `prompts.py`
- Implementado `final_summary_node()` em `nodes.py` para consolidação metacognitiva
- Refatorado `route_algorithm()` para direcionar para `final_summary_node` em caso de aprovação
- Registrado nó `final_summary_node` em `workflow.py` com aresta para `END`

### 2025-07-25 - Início da Fase 2
- Criado pacote `simulation/` com `__init__.py`
- Declarado `StudentProfile` em `simulation/schema.py` (Pydantic v2)
- Implementado `run_student_turn()` em `simulation/student_agent.py` com lógica estocástica
- Implementado `SimulationOrchestrator` em `simulation/orchestrator.py` com loop via `stream()`

### 2025-07-25 - Início da Fase 3
- Criado `profiles.py` com 4 perfis discentes pré-configurados (Ana, Carlos, Maria, Pedro)
- Criado `run_simulation.py` com CLI (`argparse`) e distribuição uniforme de sessões
- Adicionado delay configurável entre requisições LLM (padrão: 65s)

### 2025-07-26 - Correções e Melhorias
- Implementado salvamento incremental de sessões em JSONL (append a cada sessão finalizada)
- Removido delay entre sessões, mantendo apenas delay entre chamadas LLM individuais
- Corrigido bug `ValueError: Model does not support model prefilling` com função `_ensure_last_message_is_human()`

### 2026-07-30 - Início da Fase 4
- Confirmada instalação do DeepEval 4.1.4 com pandas 3.0.5 e pydantic 2.13.4
- Validada compatibilidade da API: `LLMTestCaseParams` é deprecated (alias de `SingleTurnParams`); `ContextualRelevancyMetric` existe; `ConversationalRelevancyMetric` NÃO existe no 4.1.4
- Decisão: usar instância `GeminiModel(model=DEFAULT_MODEL)` passada às métricas GEval (padrão documentado do DeepEval); API key `GOOGLE_API_KEY` lida automaticamente do ambiente
- Criado pacote `tests/` com `__init__.py`, `eval_metrics.py` e `benchmark_paper.py`
- Implementadas 4 métricas: SocraticAlignment, ScaffoldingEffectiveness, CT Progression e ContextualRelevancy
- Implementado `clean_message_content()` para normalizar content blocks stringificados do trace (`"[{'type': 'text', ...}]"`)
- Pipeline usa `DEFAULT_MODEL` de `llm_factory.py` como fonte centralizada do modelo
- Atualizado `AGENTS.md`: 6 ocorrências de `gemini-3.1-flash-lite-preview` → `gemini-3.5-flash-lite`; `LLMTestCaseParams` → `SingleTurnParams`; `ConversationalRelevancyMetric` → `ContextualRelevancyMetric`; import local `from eval_metrics import`
- Diagnóstico do dataset: 8 sessões existentes TODAS incompletas (`completed=False`, 15 turnos, travadas em `decomposition`); conteúdo do trace precisa de limpeza
- Plano: executar piloto do benchmark com as 8 sessões; regenerar dataset oficial (≥10 sessões completas) em seguida

### 2026-07-31 - Fase 4: Pipeline e Piloto do Benchmark
- Corrigida a forma de fornecer o modelo: instância `GeminiModel(model=DEFAULT_MODEL)` passada às métricas (string `"gemini-..."` faz o `initialize_model()` do DeepEval cair no fallback `GPTModel` e exigir `OPENAI_API_KEY`)
- Adicionados `evaluation_steps` às 4 métricas G-Eval: elimina a chamada extra de `_a_generate_evaluation_steps` (1 chamada LLM por métrica/caso em vez de 2)
- Descoberto limite do free tier do Gemini: **15 req/min por modelo** (`gemini-3.5-flash-lite`); rajadas acima disparam 429 `RESOURCE_EXHAUSTED`
- `benchmark_paper.py` refatorado: processamento em lotes (`--batch-size`, padrão 2) com pausa (`--sleep`, padrão 70s) entre lotes + retry automático (`_evaluate_with_retry`, 5 tentativas) para erros transitórios (429/503); amostragem via `--max-cases`; imports não utilizados removidos
- Fixado bug de agregação: `metric_data.name` do DeepEval carrega o sufixo `[GEval]` (`"Socratic Alignment Metric [GEval]"`), quebrava o match do resumo; agora as colunas são localizadas por prefixo
- Fixado nome do índice da tabela resumo (`Metric` em vez de `Unnamed: 0`)
- **Piloto executado com sucesso**: 8 casos (turnos tutor-após-aluno) × 4 métricas = 32 julgamentos; 100% de sucesso e scores 1.000 (amostra pequena, esperado dado o comportamento consistente do tutor)
- CSVs gerados: `paper_benchmark_detailed_results.csv` (8 linhas com score/success/reasoning por métrica) e `paper_benchmark_summary_table.csv`
- Estimativa para o piloto completo (112 casos × 4 métricas = 448 chamadas): ~45 min no ritmo de ~10 chamadas/min impostos pela cota do free tier
- Pendência: executar o benchmark completo (112 casos) e/ou regenerar o dataset oficial (≥10 sessões completas) antes da avaliação final

## Decisões Arquiteturais

| Data | Decisão | Justificativa |
|------|---------|---------------|
| 2025-07-25 | Manter layout flat (sem `src/`) | Projeto atual não possui estrutura `src/`; evitar refatoração de imports desnecessária |
| 2025-07-25 | Focar apenas em `nodes.py` e `workflow.py` | Dashboard e API são componentes separados; refatorar core primeiro |
| 2025-07-25 | Adiar `constants.py` | Strings literais já funcionam; Enums serão adicionados na Fase 2 |
| 2025-07-25 | Migrar prompts inline para `prompts.py` | Centralização facilita experimentos de ablação para o artigo científico |
| 2025-07-25 | Implementar `final_summary_node` | Encerramento abrupto do fluxo é anti-pedagógico; síntese metacognitiva fecha o ciclo |
| 2025-07-25 | Criar subdiretório `simulation/` | Separa lógica de simulação do core do tutor; facilita manutenção |
| 2025-07-25 | Usar `stream()` no orquestrador | Mais eficiente que `invoke()`; permite observar transições intermediárias |
| 2025-07-25 | Critério de parada `current_stage == "completed"` | Alinhado com `final_summary_node` implementado na Fase 1 |
| 2025-07-25 | Usar `argparse` para CLI | Facilita experimentação com diferentes números de sessões |
| 2025-07-25 | Distribuição uniforme de perfis | Garante balanceamento para análise estatística |
| 2025-07-25 | Delay configurável entre requisições LLM | Evita rate limiting da API do Google Gemini (padrão: 65s) |
| 2025-07-26 | Salvamento incremental de sessões | Preserva sessões já finalizadas em caso de interrupção do script |
| 2025-07-26 | Garantir última mensagem é HumanMessage | Compatibilidade com API do Gemini que rejeita prefilling de assistant |
| 2026-07-30 | Usar `SingleTurnParams` em vez de `LLMTestCaseParams` | Compatibilidade com DeepEval 4.1.4 (antigo é apenas alias deprecated) |
| 2026-07-30 | Usar `ContextualRelevancyMetric` em vez de `ConversationalRelevancyMetric` | `ConversationalRelevancyMetric` não existe no DeepEval 4.1.4 (ImportError) |
| 2026-07-30 | Padronizar modelo em `gemini-3.5-flash-lite` via `DEFAULT_MODEL` | Fonte centralizada em `llm_factory.py`; AGENTS.md alinhado ao código real |
| 2026-07-30 | Passar instância `GeminiModel` às métricas | Padrão documentado do DeepEval; string `"gemini-..."` cai no fallback `GPTModel` e exige `OPENAI_API_KEY` |
| 2026-07-30 | Piloto do benchmark com dataset atual antes de regenerar | Dataset de 8 sessões incompletas serve para validar pipeline antes do dataset oficial |
| 2026-07-31 | Pré-definir `evaluation_steps` nas métricas G-Eval | Evita a chamada extra `_a_generate_evaluation_steps`; dobra a eficiência de chamadas (essencial com cota de 15 req/min) |
| 2026-07-31 | Lotes pequenos (2 casos) + pausa de 70s entre lotes | Respeita o limite de 15 req/min do free tier; rajadas maiores geram 429 |
| 2026-07-31 | Retry automático em erros transitórios (429/503) | API do Gemini retorna 503 `UNAVAILABLE` de forma intermitente; 5 tentativas com 70s de espera |
| 2026-07-31 | Localizar colunas por prefixo na síntese estatística | `metric_data.name` do DeepEval inclui sufixo `[GEval]`, inviabilizando match direto por `m.name` |

## Checklist - Fase 1 (AGENTS.md Seção 6)

- [x] Erradicar o uso da manipulação de string `.replace("_node", "")` no arquivo `nodes.py`.
- [x] Implementar o módulo de fábrica `llm_factory.py` para gerenciamento centralizado do modelo Gemini e controle de timeouts.
- [x] Padronizar a reinicialização dos atributos de controle (`approved` e `evaluation_feedback`) em todas as transições de estado do grafo.
- [x] Extrair funções utilitárias `get_last_human_message()` e `get_last_ai_message()` para `message_utils.py`.
- [x] Migrar prompts inline de `nodes.py` para `prompts.py`.
- [x] Implementar a função `final_summary_node` em `nodes.py` para consumir o histórico consolidado do Quadro-Negro (`student_artifacts`), emitir a retrospectiva pedagógica e apresentar a resolução algorítmica completa.
- [x] Refatorar a função de roteamento `route_algorithm` em `nodes.py` para direcionar o fluxo aprovado para `final_summary_node` em vez de acionar a primitiva `END`.
- [x] Registrar o nó `final_summary_node` e atualizar as arestas terminais no arquivo `workflow.py`, garantindo que a saída do resumo final transite diretamente para `END`.

## Checklist - Fase 2 (AGENTS.md Seção 6)

- [x] Declarar o modelo Pydantic `StudentProfile` no módulo `simulation/schema.py`.
- [x] Desenvolver o nó gerador de texto no arquivo `simulation/student_agent.py`, implementando a lógica estocástica de injeção de erros conceituais e impaciência.
- [x] Estruturar a classe `SimulationOrchestrator` em `simulation/orchestrator.py` para acoplar os grafos em execução cíclica autônoma, ajustando o critério de parada para aguardar a transição ao estado `"completed"` (após a execução do `final_summary_node`) antes de encerrar e gravar o log.

## Checklist - Fase 3 (AGENTS.md Seção 6)

- [x] Parametrizar no mínimo quatro perfis discentes com comportamentos contrastantes (iniciante colaborativo, intermediário impaciente, avançado conciso, propenso a erros formais).
- [ ] Rodar o orquestrador dual-agent para compilar um dataset empírico contendo pelo menos 10 sessões inteiras, exportando os dados para o arquivo `dataset_ct_tutoring.jsonl`.

## Checklist - Fase 4 (AGENTS.md Seção 6)

- [x] Instalar o pacote `deepeval` e autenticar as variáveis de ambiente necessárias.
- [x] Implementar as rubricas pedagógicas `SocraticAlignmentMetric`, `ScaffoldingEffectivenessMetric` e `PedagogicalProgressionMetric`.
- [ ] Executar o script `benchmark_paper.py` no dataset completo, gerar as tabelas estatísticas (`paper_benchmark_summary_table.csv`) e consolidar os dados descritivos para a redação científica. *(Piloto de 8 casos validado; execução completa pendente)*

## Arquivos Modificados

| Arquivo | Status | Descrição |
|---------|--------|-----------|
| `nodes.py` | Refatorado | Core do agente: imports, factory, utilitários, prompts e `final_summary_node` |
| `workflow.py` | Atualizado | Grafo com nó `final_summary_node` e aresta para `END` |
| `prompts.py` | Expandido | 11 prompts: 10 migrados + `FINAL_SUMMARY_NODE_PROMPT` |
| `llm_factory.py` | Novo | Factory centralizada do LLM com retries e timeout |
| `message_utils.py` | Novo | Funções utilitárias de extração de mensagens |
| `simulation/__init__.py` | Novo | Pacote Python para módulos de simulação |
| `simulation/schema.py` | Novo | Modelo Pydantic `StudentProfile` |
| `simulation/student_agent.py` | Novo | Função `run_student_turn()` com lógica estocástica |
| `simulation/student_agent.py` | Atualizado | Adicionada função `_ensure_last_message_is_human()` para correção de bug Gemini |
| `simulation/orchestrator.py` | Novo | Classe `SimulationOrchestrator` para loop dual-agent |
| `simulation/orchestrator.py` | Atualizado | Removido delay entre sessões |
| `profiles.py` | Novo | 4 perfis discentes pré-configurados |
| `run_simulation.py` | Novo | Script CLI para execução de simulações em batch com delay configurável |
| `run_simulation.py` | Atualizado | Salvamento incremental com `append_session_to_jsonl()` |
| `tests/__init__.py` | Novo | Pacote Python para métricas e benchmark |
| `tests/eval_metrics.py` | Novo | 4 métricas G-Eval usando `GeminiModel(model=DEFAULT_MODEL)` + `evaluation_steps` + `SingleTurnParams` |
| `tests/eval_metrics.py` | Atualizado | Modelo como instância `GeminiModel`; `evaluation_steps` pré-definidos nas 4 métricas |
| `tests/benchmark_paper.py` | Novo | Pipeline: `clean_message_content()`, `load_dataset_as_test_cases()`, `run_paper_benchmark()` |
| `tests/benchmark_paper.py` | Atualizado | Lotes com pacing (`--batch-size`/`--sleep`/`--max-cases`); `_evaluate_with_retry`; fix agregação por prefixo; índice `Metric` |
| `paper_benchmark_detailed_results.csv` | Gerado | Piloto (8 casos): scores/success/reasoning por métrica |
| `paper_benchmark_summary_table.csv` | Gerado | Piloto (8 casos): média (0.0–1.0) e taxa de sucesso por métrica |
| `AGENTS.md` | Atualizado | Modelo `gemini-3.5-flash-lite`; `SingleTurnParams`; `ContextualRelevancyMetric`; instância `GeminiModel` no blueprint da Seção 5.1; checklist Fase 4 |
| `PROGRESS.md` | Atualizado | Este arquivo |
