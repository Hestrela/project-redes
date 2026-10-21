Preditor de Falha e Risco em Dispositivos de Rede

Projeto multidisciplinar de Ciência da Computação que integra Redes de Computadores, Estrutura de Dados II e Análise e Projeto de Sistemas. Desenvolvido pelo Grupo 4 com a metodologia Scrum.

Página do projeto: Página Local

Repositório: https://github.com/ViniEduOliveira/project-redes

Integrantes do Grupo:
Vinicius Eduardo Santos de Oliveira
Giulia Ayumi Shimada Cardoso
Heitor Estrela de Andrade
Gabriel Romão da Silva
Miguel Augusto da Costa Souza

Docentes orientadores: Andrea Sakai, Denise De Souza e Luis De Oliveira.

Objetivo

Desenvolver, de forma iterativa e incremental via metodologia Scrum, uma aplicação que treine um modelo preditivo de árvore de decisão a partir de logs históricos de rede. O sistema deve disponibilizar um dashboard capaz de classificar o status dos dispositivos em tempo real, realizando o monitoramento da rede local e permitindo a injeção de eventos simulados sob demanda.

Descrição do Projeto

A aplicação coleta métricas reais de dispositivos (como latência, perda de pacotes e jitter) para treinar o algoritmo de árvore de decisão.

Em produção, o sistema conta com um dashboard em tempo real que monitora os IPs via ping e classifica o estado de cada dispositivo em três categorias: OK, RISCO ou FALHA. Além do monitoramento ao vivo, é feita a verificação da rede em cenários variados.

Estrutura do repositório:
Arquivo / pasta	Conteúdo
Memorando_de_Decisao_grupo4.md	Decisão da fonte de dados (dataset CAIDA x API RIPE Atlas) e justificativa
coleta.py	Script de coleta de medições de ping pela API do RIPE Atlas
2_Coleta_de_dados.ipynb	Notebook da etapa de coleta de dados
3_Baseline_e_Rotulagem.ipynb	Baseline e rotulagem (OK, RISCO, FALHA)
4_Arvore_Inicial.ipynb	Árvore de decisão inicial e ajuste a partir do erro

metadados/	Metadados do projeto
Como reproduzir o experimento:

1. Ambiente
Google Colab (Utilizado pelo grupo)
Python: Python 3
Bibliotecas:
matplotlib.pyplot, FancyBboxPatch, Polygon, json, json, time, urllib3, datetime, Pathlib, google.colab, requests, pandas, os, random


2. Onde baixar os dados
Os dados vêm da API pública do RIPE Atlas (https://atlas.ripe.net/api/v2/), escolhida no Memorando de Decisão em vez do dataset CAIDA Ark. O script coleta.py consulta apenas endpoints públicos de leitura e não usa chave de API.

O script faz o seguinte:

Lista as âncoras ativas do RIPE Atlas.
Para cada âncora-alvo, escolhe duas medições públicas de ping IPv4 em andamento e sorteia sondas de origem diferentes em cada uma.
Baixa os resultados das últimas 366 horas e grava tudo em medicoes_consolidadas.csv.

Parâmetros no topo do script: TOTAL_DUPLAS = 15, PROBES_POR_MEDICAO = 5, HORAS_COLETA = 366 e semente aleatória 42.


O CSV é salvo em ./ripe_atlas/raw/. No Google Colab, o script monta o Google Drive e salva em MyDrive/ripe_atlas/raw/.

Atenção: a janela de coleta é relativa ao momento da execução e as medições do RIPE Atlas continuam rodando. Por isso, uma nova coleta não devolve exatamente os mesmos registros.

3. Ordem de execução
coleta.py (ou 2_Coleta_de_dados.ipynb) para gerar medicoes_consolidadas.csv.
3_Baseline_e_Rotulagem.ipynb para calcular o baseline e rotular OK, RISCO e FALHA.
4_Arvore_Inicial.ipynb para treinar e ajustar a árvore de decisão.


Créditos e referências:
RIPE NCC. RIPE Atlas. Plataforma e API de medições de rede. Disponível em: https://atlas.ripe.net/.
CAIDA - CENTER FOR APPLIED INTERNET DATA ANALYSIS. The IPv4 Routed /24 Topology Dataset. La Jolla: CAIDA, 2008. Disponível em: https://www.caida.org/catalog/datasets/ipv4_routed_24_topology_dataset/. Acesso em: 5 set. 2026.
CAIDA - CENTER FOR APPLIED INTERNET DATA ANALYSIS. Archipelago (Ark) Monitor Locations. La Jolla: CAIDA, [s.d.]. Disponível em: https://www.caida.org/projects/ark/locations/. Acesso em: 5 set. 2026.
RIPE NCC. REST API Manual. Amsterdã: RIPE NCC, [s.d.]. Disponível em: https://atlas.ripe.net/docs/apis/rest-api-manual/. Acesso em: 5 set. 2026.
RIPE NCC. Credits. Amsterdã: RIPE NCC, [s.d.]. Disponível em: https://atlas.ripe.net/docs/getting-started/credits. Acesso em: 5 set. 2026.
RIPE NCC. Rate Limiting. Amsterdã: RIPE NCC, [s.d.]. Disponível em: https://atlas.ripe.net/docs/apis/rest-api-manual/core-concepts/rate-limiting/. Acesso em: 5 set. 2026.
RIPE NCC. RIPE Atlas Documentation. Amsterdã: RIPE NCC, [s.d.]. Disponível em: https://atlas.ripe.net/docs/. Acesso em: 5 set. 2026.
RIPE NCC. RIPE Atlas. Amsterdã: RIPE NCC, [s.d.]. Disponível em: https://www.ripe.net/analyse/internet-measurements/ripe-atlas/. Acesso em: 5 set. 2026.
RIPE NCC. RIPE Atlas. [S.l.: s.n.], 13 jan. 2017. 1 vídeo (2 min 34 s). Canal RIPE NCC. Disponível em: https://www.youtube.com/watch?v=Z3SW2vO8qW0. Acesso em: 5 set. 2026.
SAKAI, Andrea Ono. Aula 5 - Fonte de dados do projeto. Mogi das Cruzes: Cruzeiro do Sul Virtual, 2026. Material de aula em PDF.