# Taxímetro

MVP em Python/Kivy: uma tela que rastreia a corrida pelo GPS do celular e
calcula o valor em tempo real.

## Regras de tarifa (R$/km)

| Quando | Tarifa |
|---|---|
| Dia de semana, horário comercial (08h–18h) | R$ 2,00 |
| Dia de semana, fora do horário comercial (noite) | R$ 3,00 |
| Fim de semana (sábado/domingo) | R$ 3,50 |
| Fim de semana com "Festa" marcada | valor escolhido manualmente (entre R$ 2,00 e R$ 5,00) |

A tarifa é travada no momento em que a corrida é iniciada (não muda no meio
da corrida). A lógica fica isolada em [`taximetro/fare.py`](taximetro/fare.py)
e tem testes em [`tests/test_fare.py`](tests/test_fare.py).

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
3. Quando o job terminar, baixe o artefato `taximetro-apk` — é o `.apk`
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

O APK sai em `bin/taximetro-0.1.0-arm64-v8a_armeabi-v7a-debug.apk`.

## Próximos passos (fora do escopo deste MVP)

- Persistir histórico de corridas
- Tela de "corrida em andamento" separada da de configuração
- Cálculo de tempo parado (bandeira 2 tradicional) se for desejado
- Publicação assinada (release, não debug) para distribuir fora do GitHub
- Alerta de "corrida abaixo do valor justo": comparar em tempo real com
  corridas equivalentes de outros apps (Uber/99) e avisar se o valor
  calculado ficar abaixo de R$ 2,00/km. Isso depende de acesso à API/preço
  desses apps (nenhum expõe isso publicamente hoje), então precisa ser
  investigado antes de virar tarefa de implementação.
