# Correctif — clip en file d'attente

## Le seul échec restant

`FILE_QUEUED` : l'endpoint sync a accepté le fichier mais le worker n'avait pas
fini. Compté comme transcript vide, donc WER 1,0 — on reproche au modèle une file
d'attente.

L'upload est maintenant réessayé deux fois avec backoff. Ré-envoyer est moins
risqué que d'interroger un endpoint de statut dont je n'ai pas vérifié le
contrat — et j'ai assez inventé d'API aujourd'hui.

## Copier — deux fichiers

```
app\asr\sahara.py
tests\test_sahara_adapter.py
```

```powershell
Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
```

## Le run qui compte

```powershell
python -m app.benchmark.afriswitch_cli run --config kinyarwanda --limit 200 --providers sahara --out benchmark\reports
```

200 énoncés à 30 requêtes/minute ≈ **7 minutes**. Lancez-le et préparez la vidéo
pendant ce temps.

Avec une clé OpenAI, ajoutez Whisper — deux modèles mesurés valent nettement
mieux qu'un, et le rubrique demande 3+ :

```powershell
$env:WHISPER_API_KEY="sk-..."
python -m app.benchmark.afriswitch_cli run --config kinyarwanda --limit 200 --providers sahara,whisper --out benchmark\reports
```

## À coller dans le rapport de soumission

Section « Layer B — Results » de `docs\submission\benchmark-report.md`.
Remplacez le paragraphe « **Pending.** » par le tableau généré.

Et ajoutez le constat, qui est votre contribution :

> Word error rate barely separates moderate from heavy code-mixing (0.32 vs
> 0.49), while switch point preservation collapses from 0.80 to 0.17 across the
> same boundary. A model can hold its error rate and still stop reproducing the
> speaker's language alternation — which WER cannot express and a mediation case
> depends on.

Vérifiez le n et les intervalles avant de citer : à n=10 ils sont très larges.
À n=200 ils se resserrent et la comparaison devient tenable.
