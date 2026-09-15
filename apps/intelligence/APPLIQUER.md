# Correctif — nom du modèle Whisper

## Ce qui a échoué

```
The model `whisper-large-v3` does not exist or you do not have access to it.
```

`whisper-large-v3` est le nom **Hugging Face**. Sur l'API OpenAI le modèle
s'appelle **`whisper-1`**. Encore une valeur par défaut que j'avais écrite sans
la vérifier, même classe d'erreur que l'URL Intron.

**Vous n'avez rien payé** : un 404 pour modèle inexistant n'est pas facturé.

## Ce qui est ajouté

Le préflight interroge maintenant `/models/{id}` — un GET gratuit — avant de
lancer quoi que ce soit. Un nom de modèle faux était invisible jusqu'au premier
appel réel, et un run de 200 le découvrait 200 fois.

Un fournisseur sans endpoint de listing renvoie « non vérifiable » plutôt qu'une
erreur : un modèle invérifiable n'est pas un modèle absent.

## Copier

```
app\config.py                        app\asr\base.py
app\asr\whisper.py                   app\benchmark\afriswitch_runner.py
app\benchmark\afriswitch_cli.py      tests\test_sahara_adapter.py
tests\test_fallback_corpus.py        .env.example
```

```powershell
Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
```

## Lancer

```powershell
$env:WUNZI_MODE="live"
$env:WHISPER_API_KEY="sk-..."

python -m app.benchmark.afriswitch_cli run --config kinyarwanda --limit 200 --providers whisper --out benchmark\reports
```

Le préflight doit afficher :

```
  whisper: configured (https://api.openai.com/v1, whisper-1)
```

S'il affiche `Cannot run:`, rien n'est dépensé.

## Coût

`whisper-1` est facturé à la minute d'audio. Votre échantillon fait ~0,65 h
(0,20 + 0,25 + 0,20), soit environ **39 minutes** — quelques dizaines de centimes.
Commencez par `--limit 20` si vous préférez vérifier le coût réel d'abord.

## Et Sahara

**Ne relancez pas Sahara** : USD 0,03 restants ≈ 7 appels. Utilisez `rescore` sur
le JSON du run à 200 que vous avez déjà.
