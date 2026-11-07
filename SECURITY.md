# NiakVIO Brain-LLM — politique de sécurité

Seule la branche `main` actuelle est maintenue. Le projet est en version 0.x ; les anciennes références 4.x/5.x du modèle de fichier GitHub étaient fictives et ne correspondent pas à des releases.

**Signaler une vulnérabilité** : utiliser GitHub Private Vulnerability Reporting lorsque disponible, ou contacter le propriétaire en privé. Ne pas mettre de secrets, détails d'exploitation, conversations privées ou en-têtes sensibles dans les issues/discussions publiques.

## Frontières vérifiables
- Provider, pages récupérées et sortie LLM = **données non fiables** ; seul NiakVIO contrôle l'application, le SHA des octets matérialisés, le média décodé, l'identité et la non-régression.
- Les jobs manipulant des mémoires privées doivent filtrer leurs logs et artefacts. Aucun prompt source privé ni token dans les fichiers publics ou dans les uploads d'artefacts.
- Toutes les GitHub Actions externes sont épinglées à un SHA 40 caractères ; les checkouts utilisent `persist-credentials: false` pour ne pas laisser le jeton Git dans les répertoires de travail. Le test `test_workflow_supply_chain_policy.py` vérifie cela.
- Les requêtes payantes exigent explicitement `NIAKVIO_ALLOW_PAID_API=1` et une clé API. Aucune bascule automatique sur un service payant ; les appels distants sont désactivés par défaut.
- `store=false` pour les requêtes Responses OpenAI ; les API tierces doivent être évaluées selon leurs règles de confidentialité, de conservation et d'apprentissage avant utilisation.
- Un VPS faible n'est pas destiné à exécuter un LLM lourd ou une exécution non isolée de code provider ; garder les runners CI et barrières réseau distincts.

Ce fichier n'atteste ni la clôture des alertes privées CodeQL/Dependabot/secret scanning ni un niveau d'isolation parfait. Voir [NiakVIO SECURITY.md](https://github.com/niakw/NiakVIO/blob/main/SECURITY.md) et [API/cost](docs/MODEL_ROUTING_COST_2026-11-07.md).


## Vérification CodeQL du 7 novembre 2026

- Initial : une alerte High ouverte (#1, `py/incomplete-url-substring-sanitization`) dans `private_chat_memory.py` : une sous-chaîne `github.com/` ne garantit pas l'origine d'une URL. Correction `68267973`/`b3031d36`, tests `e03334b` incluant sous-domaines usurpés, userinfo, ports invalides et HTTPS.
- Après correction : [inventaire GitHub `42364586403`](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/42364586403) **0 alerte CodeQL ouverte**, [CI Brain](https://github.com/niakw/NiakVIO-Brain-LLM/actions/runs/42364094964) verte. Ne pas interpréter les retours `unavailable_not_clean` de Dependabot et Secret scanning comme 0.
- Les 11 workflows avec actions GitHub mutables ont été épinglés à des SHAs complets et les checkouts non persistants `9e322dc`/`ee40901`. Ce durcissement ne qualifie pas le moteur comme prêt pour l'envoi de mémoire privée à une API hébergée.

Rapport métier et sécurité des deux dépôts : [NiakVIO audit](https://github.com/niakw/NiakVIO/blob/main/docs/NIAKVIO_BRAIN_METIER_SECURITE_QUALITE_AUDIT_2026-11-07.md).
