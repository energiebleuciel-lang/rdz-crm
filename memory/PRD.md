# RDZ CRM - Product Requirements Document

## OBJECTIF

CRM central **RDZ** : collecte 100% des leads, separation stricte **ZR7** / **MDL**, routing immediat + distribution automatique 09h30 CSV.

## NAMING STRICT (SCHEMA FREEZE)

`phone`, `departement`, `produit`, `nom`, `entity` (ZR7|MDL)
Interdit: telephone, tel, mobile, product, product_type, crm, account, dept

## MODELES

- **Client** : `{id, entity, name, email, delivery_emails, api_endpoint, auto_send_enabled, active}`
- **Commande** : `{id, entity, client_id, produit, departements, quota_semaine, lb_percent_max, priorite, active}`
- **Provider** : `{id, name, slug, entity, api_key, active}` - fournisseur externe rattache a UNE entite
- **Delivery** : `{id, lead_id, client_id, commande_id, status, csv_content, sent_to, send_attempts, last_error}`
- **Delivery statuts** : `pending_csv` -> `ready_to_send` -> `sending` -> `sent` / `failed`
- **Lead statuts** : `new` | `routed` | `livre` | `no_open_orders` | `duplicate` | `hold_source` | `pending_config` | `invalid`
- **Settings** : `cross_entity`, `source_gating`, `forms_config`, `email_denylist`, `delivery_calendar`

## REGLES METIER (ORDRE DE PRIORITE)

1. **Calendar gating** (day OFF) -> bloque routing + batch (rien ne se passe)
2. **Client non livrable** -> aucune commande OPEN possible
3. **Commande OPEN** = `active` + `semaine courante` + `delivered < quota` + `client livrable`
4. **auto_send_enabled = false** (day ON) -> CSV genere, pas envoye -> `ready_to_send`
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

Si aucun canal valide -> client NON livrable -> commandes CLOSED.

Email denylist (configurable via settings):
- example.com, test.com, localhost, invalid, fake.com, mailinator.com

## DELIVERY LIFECYCLE

```
pending_csv -> ready_to_send -> sending -> sent
                    |              |
                 failed <----------
```

- `pending_csv`: Cree au routing, en attente du batch
- `ready_to_send`: CSV genere, en attente envoi manuel (auto_send_enabled=false)
- `sending`: Envoi en cours
- `sent`: Email accepte par SMTP
- `failed`: Erreur d'envoi (peut etre retente)

**REGLE CRITIQUE**: `lead.status = "livre"` UNIQUEMENT si `delivery.status = "sent"`

## DELIVERY STATE MACHINE (INVARIANTS)

**SEUL le module delivery_state_machine.py peut modifier delivery.status et lead.status vers sent/livre**

Invariants pour status="sent":
- sent_to DOIT etre une liste non vide
- last_sent_at DOIT etre non null
- send_attempts DOIT etre >= 1
- Violation = DeliveryInvariantError + status="failed"

Guards batch:
- batch_mark_deliveries_sent: verifie que TOUTES les deliveries sont dans un etat source valide
- batch_mark_deliveries_failed: bloque si deliveries deja en "sent" (terminal)
- batch_mark_deliveries_ready_to_send: verifie que source = "pending_csv"

## CLIENT REJECTION (REJET)

Un client peut rejeter un lead deja livre.

Comportement:
- `delivery.outcome` = "rejected" (status et CSV inchanges)
- `delivery.rejected_at`, `rejected_by`, `rejection_reason` renseignes
- `lead.status` = "new" (re-routable comme un lead frais)
- References delivery supprimees du lead ($unset)
- Le lead redevient disponible pour le routing immediat ou le batch

Billing:
- `billable = delivery.status == "sent" AND outcome == "accepted"`
- Un lead rejete n'est PAS facturable

Idempotency:
- Rejeter 2x le meme lead = pas d'erreur, retour `already_rejected: true`

Guard:
- Seul un delivery `status=sent` peut etre rejete

## DELIVERY CALENDAR

- Defaut: lundi-vendredi (jours 0-4)
- Samedi/dimanche: OFF par defaut
- Configurable par entity via settings.delivery_calendar
- **HARD STOP**: Si jour OFF -> aucune commande OPEN -> routing retourne `no_open_orders`

## AUTO_SEND_ENABLED

- Champ `auto_send_enabled` sur Client (defaut: true)
- Si `true`: batch genere CSV + envoie -> `delivery.status=sent` + `lead.status=livre`
- Si `false`: batch genere CSV + stocke -> `delivery.status=ready_to_send` + `lead.status=routed`
- Envoi manuel via `POST /api/deliveries/{id}/send` ou `POST /api/deliveries/batch/send-ready`

## ARCHITECTURE (v4.6)

```
/app/backend/
  config.py, server.py
  models/ (auth, client, commande, delivery, entity, lead, provider, setting)
  routes/ (auth, clients, commandes, deliveries, providers, public, settings)
  services/ (activity_logger, csv_delivery, daily_delivery, delivery_state_machine, duplicate_detector, routing_engine, settings)
```

## COMPLETED

- Phase 1 : Backend foundation (modeles, routing, delivery 09h30, doublon 30j, CSV ZR7/MDL, SMTP OVH)
- Audit technique (Dec 2025) : 25+ fichiers legacy supprimes, naming unifie
- Commande OPEN : active + semaine courante + delivered < quota
- Cross-entity toggle : collection settings, global ON/OFF + per-entity
- Source gating : blacklist dans settings, lead stocke hold_source
- Provider : auth API key (prov_xxx), entity locked, cross-entity interdit
- **Phase 2 (Dec 2025)** : Routing immediat dans POST /api/public/leads
- **Phase 2.1** : Delivery lifecycle strict (pending_csv -> sent/failed)
- **Phase 2.2** : Client livrable (email denylist, delivery_enabled)
- **Phase 2.3** : Calendar gating (delivery_days par entity, hard stop routing)
- **Phase 2.4** : Endpoints deliveries (list, stats, send, download, batch/generate-csv, batch/send-ready)
- **Phase 2.5** : auto_send_enabled integration
- Tests: 24/24 passes (iteration 20)
- **Phase 2.6 (Feb 2025)** : State Machine Enforcement
  - delivery_state_machine.py: seul module autorise pour transitions de status
  - Invariants stricts: sent_to, last_sent_at, send_attempts obligs pour status=sent
  - Guards batch: verification etats source, blocage terminal
  - 3 code paths corriges: batch_send_ready, batch_generate_csv, deliver_leads_to_client
  - Fallback direct DB supprime (zero bypass)
  - Dead code supprime (csv_delivery.deliver_to_client)
  - Tests: 45/45 passes (iteration 21)
- **Phase 2.7 (Feb 2025)** : Client Rejection Feature
  - Endpoint POST /api/deliveries/{id}/reject-leads
  - outcome: accepted (default) | rejected sur delivery
  - Rejet: lead.status=new, references delivery supprimees, re-routable
  - delivery.status et CSV inchanges (historique preserve)
  - billable = status=sent AND outcome=accepted
  - Idempotent: 2e rejet = pas d'erreur
  - Guard: seul status=sent peut etre rejete
  - Stats enrichis: rejected, billable
  - Teste manuellement: rejet, idempotency, billing, guard non-sent
- **Phase 3 (Feb 2025)** : UI Admin
  - Login RDZ (auth JWT, redirect /admin/dashboard)
  - Dashboard: stats deliveries (pending/ready/sent/failed/billable/rejected) + breakdown ZR7/MDL
  - Deliveries: table + filtres (status/entity) + stat pills + pagination + actions (view/download/send/resend)
  - Delivery Detail: info delivery + lead + rejection info + actions + reject modal (raison obligatoire)
  - Clients: table ZR7+MDL + edit inline (email/api_endpoint/auto_send/active) + filtre entity
  - Commandes: table + create modal + edit inline + progress bars quota + filtre entity
  - Settings: email denylist + simulation mode toggle + delivery calendar par entity
  - Navigation: sidebar collapsible + logout
  - Tests: 10/10 passes (iteration 22)
- **Phase 3.1 (Feb 2025)** : UI Enrichment
  - Cockpit dashboard: calendar banners, 11 stat cards, top clients 7d, clients non livrables, quotas faibles, stock bloque par entity/produit
  - Endpoint GET /api/leads/dashboard-stats (un seul appel = toutes les donnees)
  - Clients: phone, canaux (icones), auto_send, jours livraison, deliverable+raison, delivery count, lien deliveries
  - Deliveries: phone client, auto_send OFF indicator, last_error, filtre client_id via URL
  - Delivery detail: panneau client (tel/email/auto_send/jours), lien deliveries client
  - Settings: banners status (simulation + calendrier ZR7/MDL)
  - Backend: clients enrichis (has_valid_channel, deliverable_reason, auto_send_enabled)
  - Tests: 5/5 passes (iteration 23)
- **Phase 3.2 (Feb 2025)** : Client 360 Upgrade
  - Page detail client /admin/clients/{id} avec 4 tabs
  - Top summary: ratings (global/paiement/satisfaction/discount 1-5), client_status (VIP/Normal/Watchlist/Blocked), auto_send, next delivery day, jours calendrier
  - Performance tab: aggregation par day/week/month, sent/billable/rejected/reject_rate, breakdown produit
  - CRM & Paiement tab: status, accounting, payment_terms/method, derniers paiements, tags, notes internes
  - Activite tab: timeline rejets/MAJ CRM/notes avec timestamps
  - Backend: GET /summary, PUT /crm, POST /notes, GET /activity
  - GET /clients/{id} enrichi (has_valid_channel, deliverable_reason, auto_send_enabled, week stats)
  - Tests: 10/10 frontend + 25/25 backend (iteration 24)
- **UI3 Etape 1+2 (Feb 2025)** : Leads + Remove lead
  - Page /admin/leads: liste globale avec filtres (entity/produit/status/dept/source/search), stat pills, pagination
  - Page /admin/leads/{id}: payload brut, routing info, delivery history avec actions (view/reject/remove)
  - POST /api/deliveries/{id}/remove-lead: outcome=removed, lead→new, event_log, CSV intact, idempotent
  - Guards: status must be sent, cannot remove if rejected
  - Stats enrichis: removed count, billable exclut rejected+removed
  - Deliveries list/detail: badge removed, panel removal info
  - Tests: 10/10 frontend + 16/16 backend (iteration 25)
- **UI3 Etape 3 (Feb 2025)** : Event Log centralisé
  - services/event_logger.py: helper log_event() réutilisable
  - GET /api/event-log (filtres action/entity_type/entity/entity_id/user/search), GET /api/event-log/actions, GET /api/event-log/{id}
  - Actions instrumentées: reject_lead, lead_removed_from_delivery, send_delivery, resend_delivery, delivery_failed, order_activate, order_deactivate, client_auto_send_change, rotate_provider_key
  - Page /admin/activity: timeline globale + filtres + liens vers entités
  - ActivityBlock: composant réutilisable intégré dans Lead detail et Delivery detail
  - Tests: 10/10 frontend + 14/14 backend (iteration 26)
- **UI3 Etape 4 (Feb 2025)** : Enrichissement Commandes + Delivery + QA
  - Page /admin/commandes/{id}: config routing + quota bar + départements + historique quotas 4 sem + deliveries liées + activité + toggle active
  - GET /api/commandes/{id}/deliveries endpoint
  - Delivery detail enrichi: section SMTP log (sent_to/last_sent_at/attempts/sent_by/csv_file/error) + bouton Retirer lead + remove modal
  - Commandes list: bouton view vers detail
  - Bug fix: dashboard-stats billable excluait seulement rejected mais pas removed → corrigé ($nin)
  - QA COMPLÈTE: 12/12 areas PASS, 23/23 backend tests (iteration 27)
    - Navigation 7 items, Dashboard cockpit, Deliveries list+detail, Leads list+detail
    - Clients list+360, Commandes list+detail, Activity timeline, Settings
    - Compteurs cohérence: sent=160, rejected=2, removed=1, billable=157 (160-2-1=157)
    - Actions sensibles: reject/remove/toggle tous fonctionnels + event logged
    - Idempotence: reject 2x=already_rejected, remove 2x=already_removed
- **Départements V1 (Feb 2026)** : Pilotage industriel
  - Page /admin/departements: table (dept, produit) avec filtres (product/period/week/dept/status)
  - GET /api/departements/overview: vue globale avec produced, billable, non_billable, quota, remaining, status, clients_covering
  - GET /api/departements/{dept}/detail: drawer avec KPIs, timeseries 8 semaines (recharts BarChart), clients couvrants
  - GET /api/clients/{id}/coverage: couverture client par département avec agrégats
  - Statuts calculés: no_order / on_remaining / saturated / inactive_blocked
  - Comparatif semaine N vs N-1 sur produced (Δ%)
  - Tab "Client Coverage": sélecteur client, KPI agrégés, table dept par dept
  - Navigation: Départements ajouté à la sidebar (MapPin icon)
  - Wildcard departements (*) supporté dans la couverture commandes
  - Tests: 25/25 backend + 100% frontend (iteration 28)

## NEXT

- [ ] Permissions simples (admin / ops / viewer)
- [ ] Pricing Engine (moteur de tarification)

## BACKLOG

- Dashboard stats avancés (filtres, graphiques)
- Breakdown par produit sur le dashboard
- Livraison API POST pour clients
- Facturation inter-entités
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
| GET | /api/clients/{id}/coverage | Oui | Couverture depts client |
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
| POST | /api/deliveries/{id}/reject-leads | Admin | Rejet client |
| POST | /api/deliveries/batch/generate-csv | Admin | Generer CSV en batch |
| POST | /api/deliveries/batch/send-ready | Admin | Envoyer ready_to_send |
| GET | /api/departements/overview | Oui | Vue globale depts |
| GET | /api/departements/{dept}/detail | Oui | Detail dept (drawer) |
| POST | /api/public/leads | Non/Key | Soumettre lead + routing |
| POST | /api/public/track/* | Non | Tracking events |

## KEY FILES

- `/app/backend/server.py` - FastAPI app, routes, scheduler 09h30
- `/app/backend/services/delivery_state_machine.py` - SEUL module pour transitions status delivery/lead
- `/app/backend/services/routing_engine.py` - route_lead (calendar gating, client deliverable)
- `/app/backend/services/daily_delivery.py` - process_pending_csv_deliveries, run_daily_delivery
- `/app/backend/services/settings.py` - is_delivery_day_enabled, get_email_denylist_settings
- `/app/backend/models/client.py` - check_client_deliverable
- `/app/backend/models/delivery.py` - DeliveryStatus, VALID_STATUS_TRANSITIONS
- `/app/backend/routes/deliveries.py` - list, stats, send, download, batch
