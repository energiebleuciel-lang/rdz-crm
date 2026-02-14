# RDZ CRM - Product Requirements Document

## OBJECTIF

CRM central **RDZ** : collecte 100% des leads, separation stricte **ZR7** / **MDL**, routing immediat + distribution automatique 09h30 CSV.

## NAMING STRICT (SCHEMA FREEZE)

`phone`, `departement`, `produit`, `nom`, `entity` (ZR7|MDL)
❌ Interdit: telephone, tel, mobile, product, product_type, crm, account, dept

## MODELES

- **Client** : `{id, entity, name, email, delivery_emails, api_endpoint, auto_send_enabled, active}`
- **Commande** : `{id, entity, client_id, produit, departements, quota_semaine, lb_percent_max, priorite, active}`
- **Provider** : `{id, name, slug, entity, api_key, active}` - fournisseur externe rattache a UNE entite
- **Delivery** : `{id, lead_id, client_id, commande_id, status, csv_content, sent_to, send_attempts, last_error}`
- **Delivery statuts** : `pending_csv` → `ready_to_send` → `sending` → `sent` / `failed`
- **Lead statuts** : `new` | `routed` | `livre` | `no_open_orders` | `duplicate` | `hold_source` | `pending_config` | `invalid`
- **Settings** : `cross_entity`, `source_gating`, `forms_config`, `email_denylist`, `delivery_calendar`

## REGLES METIER (ORDRE DE PRIORITE)

1. **Calendar gating** (day OFF) → bloque routing + batch (rien ne se passe)
2. **Client non livrable** → aucune commande OPEN possible
3. **Commande OPEN** = `active` + `semaine courante` + `delivered < quota` + `client livrable`
4. **auto_send_enabled = false** (day ON) → CSV genere, pas envoye → `ready_to_send`
5. **Doublon 30j** = meme phone + produit + client = bloque, fallback autre client
6. **LB** = non livre > 8 jours, exporte comme lead normal
7. **Provider** = auth par API key -> entity verrouillee, jamais de cross-entity
8. **Cross-entity** = ZR7<->MDL fallback, controle par settings (global + per-entity)
9. **Source gating** = blacklist, lead stocke en hold_source, jamais route
10. **Form mapping** = form_code -> entity + produit via settings.forms_config

## CLIENT LIVRABLE

Un client est **livrable** si:
- Email principal valide ET pas en denylist OU
- delivery_emails contient au moins 1 email valide ET pas en denylist OU
- api_endpoint configure

Si aucun canal valide → client NON livrable → commandes CLOSED.

Email denylist (configurable via settings):
- example.com, test.com, localhost, invalid, fake.com, mailinator.com

## DELIVERY LIFECYCLE

```
pending_csv → ready_to_send → sending → sent
                    ↓              ↓
                 failed ←────────────
```

- `pending_csv`: Cree au routing, en attente du batch
- `ready_to_send`: CSV genere, en attente envoi manuel (auto_send_enabled=false)
- `sending`: Envoi en cours
- `sent`: Email accepte par SMTP
- `failed`: Erreur d'envoi (peut etre retente)

**REGLE CRITIQUE**: `lead.status = "livre"` UNIQUEMENT si `delivery.status = "sent"`

## DELIVERY CALENDAR

- Defaut: lundi-vendredi (jours 0-4)
- Samedi/dimanche: OFF par defaut
- Configurable par entity via settings.delivery_calendar
- **HARD STOP**: Si jour OFF → aucune commande OPEN → routing retourne `no_open_orders` avec `reason: delivery_day_disabled`

## AUTO_SEND_ENABLED

- Champ `auto_send_enabled` sur Client (defaut: true)
- Si `true`: batch genere CSV + envoie → `delivery.status=sent` + `lead.status=livre`
- Si `false`: batch genere CSV + stocke → `delivery.status=ready_to_send` + `lead.status=routed`
- Envoi manuel via `POST /api/deliveries/{id}/send` ou `POST /api/deliveries/batch/send-ready`

## ARCHITECTURE (v4.5)

```
/app/backend/
  config.py, server.py
  models/ (auth, client, commande, delivery, entity, lead, provider, setting)
  routes/ (auth, clients, commandes, deliveries, providers, public, settings)
  services/ (activity_logger, csv_delivery, daily_delivery, duplicate_detector, routing_engine, settings)
```

## COMPLETED

- Phase 1 : Backend foundation (modeles, routing, delivery 09h30, doublon 30j, CSV ZR7/MDL, SMTP OVH)
- Audit technique (Dec 2025) : 25+ fichiers legacy supprimes, naming unifie
- Commande OPEN : active + semaine courante + delivered < quota
- Cross-entity toggle : collection settings, global ON/OFF + per-entity
- Source gating : blacklist dans settings, lead stocke hold_source
- Provider : auth API key (prov_xxx), entity locked, cross-entity interdit
- **Phase 2 (Dec 2025)** : Routing immediat dans POST /api/public/leads
- **Phase 2.1** : Delivery lifecycle strict (pending_csv → sent/failed)
- **Phase 2.2** : Client livrable (email denylist, delivery_enabled)
- **Phase 2.3** : Calendar gating (delivery_days par entity, hard stop routing)
- **Phase 2.4** : Endpoints deliveries (list, stats, send, download, batch/generate-csv)
- Tests: 26/26 passes (iteration 19)

## NEXT (Phase 2.5 + Phase 3)

### Phase 2.5 — Mode Manuel + Actions (Backend)
- [ ] Toggle `auto_send_enabled` par client (existe mais non utilise dans batch)
- [ ] Batch CSV skip envoi si auto_send_enabled=false → status=ready_to_send
- [ ] Bouton "Envoyer maintenant" pour ready_to_send

### Phase 3 — UI Admin
- [ ] UI Clients (email, api_endpoint, auto_send_enabled, delivery_days)
- [ ] UI Commandes (OPEN/CLOSED, quotas, stats semaine)
- [ ] UI Deliveries (status, send_attempts, last_error, boutons)
- [ ] UI forms_config (form_code → entity/produit)
- [ ] UI Settings (cross-entity, source gating, email denylist, calendar)
- [ ] Dashboard minimal (stats par status/entity/produit)

## BACKLOG

- Dashboard stats avances (filtres, graphiques)
- Livraison API POST pour clients
- Feature rejet_client (client rejette un lead livre)
- Facturation inter-entites
- Audit final E2E + tracking scripts

## CREDENTIALS

- UI: `energiebleuciel@gmail.com` / `92Ruemarxdormoy`
- SMTP ZR7: `vos-leads@zr7-digital.fr` / `@92Ruemarxdormoy`
- SMTP MDL: `livraisonleads@maisonduleads.fr` / `@92Ruemarxdoy`
- Provider test: `prov_0vVMbevPVC1yBXXb3cPKySmiB_iP4nW1cjTjIOQ54is` (ZR7)

## API ENDPOINTS

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/auth/login | Non | Connexion |
| GET | /api/auth/me | Oui | Info user |
| CRUD | /api/clients | Oui | Gestion clients |
| CRUD | /api/commandes | Oui | Gestion commandes |
| CRUD | /api/providers | Admin | Gestion providers |
| POST | /api/providers/{id}/rotate-key | Admin | Regenerer API key |
| GET | /api/settings | Oui | Liste settings |
| GET/PUT | /api/settings/cross-entity | Admin | Toggle cross-entity |
| GET/PUT | /api/settings/source-gating | Admin | Source blacklist |
| GET/PUT | /api/settings/forms-config | Admin | Form mapping |
| GET/PUT | /api/settings/email-denylist | Admin | Denylist emails |
| GET/PUT | /api/settings/delivery-calendar | Admin | Calendrier livraison |
| GET | /api/settings/delivery-calendar/check/{entity} | Oui | Check jour livrable |
| GET | /api/deliveries | Oui | Liste deliveries |
| GET | /api/deliveries/stats | Oui | Stats par status |
| GET | /api/deliveries/{id} | Oui | Detail delivery |
| GET | /api/deliveries/{id}/download | Oui | Telecharger CSV |
| POST | /api/deliveries/{id}/send | Admin | Envoyer/Renvoyer |
| POST | /api/deliveries/batch/generate-csv | Admin | Generer CSV en batch |
| POST | /api/public/leads | Non/Key | Soumettre lead + routing |
| POST | /api/public/track/* | Non | Tracking events |

## KEY FILES

- `/app/backend/server.py` - FastAPI app, routes, scheduler 09h30
- `/app/backend/services/routing_engine.py` - route_lead (calendar gating, client deliverable)
- `/app/backend/services/daily_delivery.py` - process_pending_csv_deliveries, run_daily_delivery
- `/app/backend/services/settings.py` - is_delivery_day_enabled, get_email_denylist_settings
- `/app/backend/models/client.py` - check_client_deliverable
- `/app/backend/models/delivery.py` - DeliveryStatus, VALID_STATUS_TRANSITIONS
- `/app/backend/routes/deliveries.py` - list, stats, send, download, batch
