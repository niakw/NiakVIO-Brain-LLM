# Brain multi-rôles et coûts API — 7 novembre 2026

## Architecture recommandée pour un VPS léger

On ne cherche **pas** à faire tourner trois LLM sur le VPS. Plusieurs *rôles* peuvent utiliser le même moteur, ou zéro modèle pour les opérations déterministes :

1. **Observer / trier** (code déterministe + RAG + preuves réseau/TMDB) : gratuit, sans IA par défaut. Qwen local 3B reste facultatif pour condenser les faits.
2. **Générateur économique à la demande** : comparer `gpt-6-luna` (API OpenAI) et `gpt-6.1-terra` ; tester éventuellement `gemini-2.5-flash-lite` avec données publiques nettoyées.
3. **Générateur fort / critique en escalade** : `gpt-6.1-sol` pour un vrai blocage de génération non résolu, `gpt-6-astra` uniquement pour quelques familles difficiles.
4. **Validateur strict et indépendant** : code déterministe NiakVIO, SHA exact appliqué, octets exécutés, vraie lecture décodée, TMDB/S00/mini-série/saison/épisode, non-régression.
5. **Learning** : garder patterns prouvés et négatifs, fingerprint mutation+source+famille ; éviter les tentatives identiques, pas de plafond arbitraire du nombre d'hypothèses utiles.

L'adaptateur OpenAI Responses existe déjà. `gpt-6-luna` et `gpt-6.1-terra` sont maintenant autorisés **uniquement sur sélection explicite** avec la garde `NIAKVIO_ALLOW_PAID_API=1`. Aucun routeur automatique, aucune clé, aucun appel payant activé. La CI reste sans API distante.

## Tarifs publics — USD / million de tokens

| Modèle | Entrée | Sortie | 6k en entrée + 1,2k en sortie | 10 000 appels identiques |
| --- | ---: | ---: | ---: | ---: |
| OpenAI `gpt-6-luna` | $0.10 | $0.50 | $0.0012 | $12 |
| OpenAI `gpt-6.1-terra` | $1.00 | $5.00 | $0.012 | $120 |
| OpenAI `gpt-6.1-sol` | $2.00 | $10.00 | $0.024 | $240 |
| OpenAI `gpt-6-astra` | $10.00 | $50.00 | $0.12 | $1 200 |
| Gemini `gemini-2.5-flash-lite` | $0.10 | $0.40 | $0.00108 | $10.80 |
| Gemini `gemini-3.1-flash-lite` | $0.25 | $1.50 | $0.0033 | $33 |

Hypothèses sans cache, coûts d'outils, surcharge et tokens de raisonnement supplémentaires. Les longs prompts, les sorties prolongées et les usages CI/stockage peuvent coûter davantage. En mix purement indicatif, 85 % Luna + 15 % Sol sur 10 000 appels de ce format : environ **$46.20**. Sources : [OpenAI](https://developers.openai.com/api/docs/pricing), [Gemini](https://ai.google.dev/gemini-api/docs/pricing).

## Gratuit ?

- **Gemini Free Tier** : certains modèles ont des tokens gratuits sous limites RPM/TPM/RPD ; le contenu du niveau gratuit peut servir à améliorer les produits Google. Ne jamais y transmettre de mémoire privée ou de clés.
- **OpenRouter modèles `:free`** : prix modèle 0$, mais typiquement 50 requêtes/jour (jusqu'à 1 000/jour avec achat de crédits) et limites fournisseur ; les essais ratés comptent.
- **Groq Free/Developer** : quotas RPM/TPM/TPD/RPD différents par modèle/compte. Les 8 000 TPM documentés sur certaines familles peuvent bloquer les prompts de code longs.
- **ChatGPT Plus ne couvre pas la facture API.** Un VPS faible suffit pour planifier/synchroniser les preuves, pas pour exécuter de gros modèles.

Sources : [OpenRouter](https://openrouter.ai/collections/free-models), [Groq](https://console.groq.com/docs/rate-limits), [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Optimisation sans plafonner les tentatives

Chaque essai doit ajouter une information **causale** ou une hypothèse distincte. Dédupliquer sans appeler le modèle les mêmes patches, mêmes symptômes déjà épuisés, les no-op et suppressions. Utiliser RAG, signatures, compression, cache, batch, escalade selon qualité des preuves ; faire les vérifications syntaxiques et les probes basiques sans LLM. Suivre coût estimé puis réel par fournisseur, famille, provider, SHA, prompt cache et nombre de médias réellement validés. Définir des **alertes et un plafond monétaire global configurable** (pas un plafond de nombres d'essais) : à dépassement, arrêter la dépense, continuer les actions non facturantes et conserver le travail pour reprise. Une API « gratuite et illimitée » n'est pas un fondement stable pour ~800 hubs.

### Qualification obligatoire

Comparer les modèles sur un même SHA et des fixtures vraiment représentatives : film, TV normale, animé, S00/mini-série avec oracles et cas négatifs, identité terminale, qualité, langues et lecteurs multiples. Mesurer cause proposée, génération, compilation, application, matérialisation, vraie vidéo décodée, erreurs d'identité et coût réel. **Aucun benchmark API réel n'a encore validé la meilleure combinaison.** Les backends Gemini/Groq/OpenRouter et le routeur de coûts sont documentés ici, pas implémentés.

## Garde-fou budgétaire exécutable (7 novembre 2026)

Le backend OpenAI Responses propose maintenant un **registre monétaire partagé facultatif**, sans changement du backend local et sans activation implicite des API :

```sh
# À définir uniquement lorsque les appels payants sont explicitement autorisés :
export NIAKVIO_API_BUDGET_USD=5.00
export NIAKVIO_API_BUDGET_LEDGER=/var/lib/niakvio/private-api-budget.json
# Les deux barrières existantes restent nécessaires :
# NIAKVIO_ALLOW_PAID_API=1 et NIAKVIO_OPENAI_API_KEY via secret.
```

L'adaptateur réserve une estimation prudente *avant* l'appel puis comptabilise les tokens retournés par la réponse sous un verrou de fichier. Un usage absent ou un appel interrompu **conserve sa réservation** pour ne pas offrir de dépassement silencieux. Le fichier ne contient ni prompt, ni source provider, ni secret, uniquement des sommes agrégées et des compteurs. La limite porte sur les USD, **jamais sur un nombre de tentatives**.

**Limite importante :** des runners GitHub distincts ne partagent pas automatiquement ce fichier ; il faut un stockage commun transactionnel ou un budget géré par un service central pour garantir un plafond entre machines. Les tarifs et estimations doivent être revalidés auprès du fournisseur. Le budget local ne remplace pas les alertes/quotas de facturation du compte API. Les appels API restent désactivés par défaut. Tests : `tests/test_api_cost.py` et `tests/test_hosted_backend.py`.
