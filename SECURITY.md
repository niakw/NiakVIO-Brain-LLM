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
