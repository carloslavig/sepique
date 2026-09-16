# Se Pique

MVP em Python/Kivy: uma tela que rastreia a corrida pelo GPS do celular e
calcula o valor em tempo real (taxímetro).

## Regras de tarifa

A corrida começa com uma **bandeirada de R$ 12,00** e soma o valor por km
rodado em cima disso.

| Quando | Tarifa por km |
|---|---|
| Dia de semana, horário comercial (08h–18h) | R$ 2,00 |
| Dia de semana, fora do horário comercial (noite) | R$ 3,00 |
| Fim de semana (sábado/domingo) | R$ 3,50 |
| Fim de semana com "Festa" marcada | valor escolhido manualmente (entre R$ 2,00 e R$ 5,00) |

A tarifa é travada no momento em que a corrida é iniciada (não muda no meio
da corrida). A lógica fica isolada em [`taximetro/fare.py`](taximetro/fare.py)
e tem testes em [`tests/test_fare.py`](tests/test_fare.py).

### Taxa de espera (trânsito parado)

O ritmo esperado é 1 km a cada 3 minutos. Se o carro ficar abaixo disso, soma
R$ 0,60 por minuto adicional que continuar devendo essa distância, até
cumprir o 1 km (aí o ciclo de 3 minutos reinicia). Lógica em
[`WaitingFeeTracker`](taximetro/fare.py), testada em
[`tests/test_waiting.py`](tests/test_waiting.py).

## Nome/telefone do cliente e histórico

Antes de iniciar a corrida dá pra preencher (opcionalmente) o nome e telefone
do cliente. Ao finalizar, a corrida é salva num banco SQLite local
(`taximetro/storage.py`, testado em `tests/test_storage.py`), guardado na
pasta de dados do app no celular. O menu no canto superior esquerdo (botão
"=") abre o histórico com todas as corridas já feitas, mais recentes
primeiro.

## "Vale a corrida?" — analisar pedidos de outros apps

Tela acessível pelo menu ("=" no topo). Regra: o valor oferecido precisa
cobrir pelo menos R$ 2,00 por km, contando a distância até o passageiro +
a distância da corrida. Lógica pura em
[`taximetro/offer.py`](taximetro/offer.py), testada em
[`tests/test_offer.py`](tests/test_offer.py).

Duas formas de preencher os campos:

1. **Manual** — sempre funciona: você digita o que o outro app mostrou
   (distância até o passageiro, distância da corrida, valor) e toca em
   "Analisar".
2. **Automática** (best-effort) — um serviço de Acessibilidade do Android
   (`android-extra/src/.../RideOfferAccessibilityService.java`) lê a tela
   quando o Urbano Norte, inDriver ou PopMove mostram um pedido, escreve
   os textos encontrados num arquivo que o Python lê e interpreta
   (`taximetro/offer_bridge.py` + `parse_offer_texts` em
   `taximetro/offer.py`), e mostra uma **bolha flutuante por cima do outro
   app** avisando "pedido detectado" — tocar nela abre o Se Pique direto.
   Exige **duas ativações manuais** (o Android exige que sejam manuais,
   por segurança — nenhum app pode ligar isso sozinho), as duas com atalho
   direto na tela "Vale a corrida?":
   1. Configurações → Acessibilidade → Se Pique
   2. Configurações → Apps → Se Pique → Exibir sobre outros apps
      (permissão `SYSTEM_ALERT_WINDOW`)

   **Importante:** a extração automática é uma heurística (procura "R$" e
   "km" no texto da tela) que não foi validada contra as telas reais
   desses 3 apps — só dá pra afinar isso testando no aparelho de verdade e
   ajustando `parse_offer_texts` conforme o que realmente aparecer. Se não
   funcionar bem, o modo manual continua ali do lado, garantido.

## Rodando no computador (para testar a interface)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

No Windows/desktop o GPS não é suportado pelo Plyer — o app abre normalmente
e mostra "GPS não disponível", mas dá pra ver a tela e testar o botão de
Festa/slider. O teste de verdade é no Android.

Testes da lógica de tarifa e distância:

```bash
pytest
```

## Gerando o APK para Android

O Buildozer (ferramenta que empacota o app Kivy em APK) **não roda no
Windows** — só em Linux/WSL ou via CI. Duas opções:

### Opção A — GitHub Actions (recomendado, mais simples)

1. Suba este projeto para um repositório no GitHub.
2. Vá em Actions → "Build APK" → "Run workflow" (ou basta dar push na
   branch `main`, o workflow já está configurado em
   [`.github/workflows/build-apk.yml`](.github/workflows/build-apk.yml)).
3. Quando o job terminar, baixe o artefato `sepique-apk` — é o `.apk`
   pronto pra instalar no celular (ative "instalar de fontes desconhecidas"
   no Android).

### Opção B — WSL local

```bash
# dentro do WSL (Ubuntu)
sudo apt update && sudo apt install -y python3-pip build-essential git \
    openjdk-17-jdk unzip
pip install buildozer cython
buildozer android debug
```

O APK sai em `bin/sepique-0.1.0-arm64-v8a_armeabi-v7a-debug.apk`.

**Depois de um checkout limpo do python-for-android** (ele mora dentro de
`.buildozer/`, que fica fora do git), rode
`python3 scripts/patch_p4a.py <caminho para .../platform/python-for-android>`
pra reaplicar os ajustes manuais feitos nele (versão do pip fixada,
flags extras no pip install pra aceitar wheels Android, e o `<service>` do
Acessibilidade injetado no template do manifesto — nenhum dos três tem um
jeito oficial de configurar via `buildozer.spec`).

## Próximos passos (fora do escopo deste MVP)

- Tela de "corrida em andamento" separada da de configuração
- Publicação assinada (release, não debug) para distribuir fora do GitHub
- Alerta de "corrida abaixo do valor justo": comparar em tempo real com
  corridas equivalentes de outros apps (Uber/99) e avisar se o valor
  calculado ficar abaixo de R$ 2,00/km. Isso depende de acesso à API/preço
  desses apps (nenhum expõe isso publicamente hoje), então precisa ser
  investigado antes de virar tarefa de implementação.
