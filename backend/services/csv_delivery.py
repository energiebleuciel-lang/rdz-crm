"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - Service de Livraison CSV                                          ║
║                                                                              ║
║  FORMAT CSV FINAL (7 colonnes EXACTES):                                      ║
║  1. nom                                                                      ║
║  2. prenom                                                                   ║
║  3. telephone                                                                ║
║  4. email                                                                    ║
║  5. departement                                                              ║
║  6. proprietaire_maison (toujours TRUE)                                      ║
║  7. produit                                                                  ║
║                                                                              ║
║  RÈGLE LB:                                                                   ║
║  - Un lead LB est exporté comme un lead NORMAL                               ║
║  - Aucune mention "LB" dans le CSV                                           ║
║  - Le champ produit = produit de la COMMANDE (pas l'original du lead)        ║
║                                                                              ║
║  EMAILS PROFESSIONNELS:                                                      ║
║  - Templates différents par entité (ZR7 / MDL)                               ║
║  - Aucune mention technique, debug, test                                     ║
║  - Ton institutionnel, sobre, professionnel                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import csv
import io
import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone
from typing import List, Dict, Optional
from config import db, now_iso

logger = logging.getLogger("csv_delivery")

# Colonnes CSV par entité - FORMAT FINAL VERROUILLÉ
CSV_COLUMNS_ZR7 = [
    "nom",
    "prenom", 
    "telephone",
    "email",
    "departement",
    "proprietaire_maison",
    "produit"
]

CSV_COLUMNS_MDL = [
    "nom",
    "prenom", 
    "telephone",
    "email",
    "departement",
    "proprietaire",
    "type_logement",
    "produit"
]

# Templates email par entité - PRODUCTION
EMAIL_TEMPLATES = {
    "ZR7": {
        "signature": "ZR7 Consulting",
        "body": """Bonjour,

Veuillez trouver ci-joint votre livraison de leads du jour.

L'équipe ZR7 Consulting vous accompagne dans la croissance de vos performances commerciales.

Bien cordialement,
ZR7 Consulting"""
    },
    "MDL": {
        "signature": "Maison du Lead",
        "body": """Bonjour,

Veuillez trouver ci-joint votre livraison de leads du jour.

L'équipe Maison du Lead vous souhaite une excellente transformation et de belles ventes.

Cordialement,
Maison du Lead"""
    }
}


def generate_csv_content(leads: List[Dict], produit: str, entity: str) -> str:
    """
    Génère le contenu CSV à partir d'une liste de leads
    
    FORMAT FINAL VERROUILLÉ:
    ========================
    
    ZR7 (7 colonnes):
    - nom ← lead.nom
    - prenom ← lead.prenom
    - telephone ← lead.phone
    - email ← lead.email
    - departement ← lead.departement
    - proprietaire_maison ← CONSTANTE "oui"
    - produit ← produit (commande)
    
    MDL (7 colonnes):
    - nom ← lead.nom
    - prenom ← lead.prenom
    - telephone ← lead.phone
    - email ← lead.email
    - departement ← lead.departement
    - type_logement ← CONSTANTE "maison"
    - produit ← produit (commande)
    
    RÈGLES:
    - Ignore tous les autres champs du lead
    - Constantes forcées quoi qu'il arrive
    - LB invisible: produit = commande (pas original)
    """
    output = io.StringIO()
    
    if entity == "MDL":
        # MDL: 8 colonnes avec proprietaire = oui + type_logement = maison
        writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS_MDL)
        writer.writeheader()
        
        for lead in leads:
            row = {
                "nom": lead.get("nom", ""),
                "prenom": lead.get("prenom", ""),
                "telephone": lead.get("phone", ""),
                "email": lead.get("email", ""),
                "departement": lead.get("departement", ""),
                "proprietaire": "oui",  # CONSTANTE - toujours "oui"
                "type_logement": "maison",  # CONSTANTE - toujours "maison"
                "produit": produit  # Produit de la COMMANDE (relabel LB)
            }
            writer.writerow(row)
    else:
        # ZR7: 7 colonnes avec proprietaire_maison = oui
        writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS_ZR7)
        writer.writeheader()
        
        for lead in leads:
            row = {
                "nom": lead.get("nom", ""),
                "prenom": lead.get("prenom", ""),
                "telephone": lead.get("phone", ""),
                "email": lead.get("email", ""),
                "departement": lead.get("departement", ""),
                "proprietaire_maison": "oui",  # CONSTANTE - toujours "oui"
                "produit": produit  # Produit de la COMMANDE (relabel LB)
            }
            writer.writerow(row)
    
    return output.getvalue()


def generate_csv_filename(entity: str, produit: str) -> str:
    """
    Génère un nom de fichier CSV professionnel
    Format: {ENTITY}_{PRODUIT}_{YYYY-MM-DD}.csv
    
    Exemples:
    - ZR7_PV_2026-02-13.csv
    - MDL_PAC_2026-02-13.csv
    """
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{entity}_{produit}_{date_str}.csv"


async def send_csv_email(
    entity: str,
    to_emails: List[str],
    csv_content: str,
    csv_filename: str,
    lead_count: int,
    lb_count: int,
    produit: str
) -> Dict:
    """
    Envoie un email PROFESSIONNEL avec le CSV en pièce jointe
    
    Templates différents par entité (ZR7 / MDL)
    Aucune mention technique, debug, test
    
    Args:
        entity: ZR7 ou MDL
        to_emails: Liste des emails destinataires
        csv_content: Contenu du CSV
        csv_filename: Nom du fichier (format: {ENTITY}_{PRODUIT}_{DATE}.csv)
        lead_count: Nombre total de leads
        lb_count: Nombre de leads LB inclus
        produit: Type de produit
    
    Returns:
        Dict avec status et détails
    """
    # Configuration SMTP selon entité
    smtp_config = {
        "ZR7": {
            "host": "ssl0.ovh.net",
            "port": 465,
            "email": "vos-leads@zr7-digital.fr",
            "password_env": "ZR7_SMTP_PASSWORD"
        },
        "MDL": {
            "host": "ssl0.ovh.net",
            "port": 465,
            "email": "livraisonleads@maisonduleads.fr",
            "password_env": "MDL_SMTP_PASSWORD"
        }
    }
    
    config = smtp_config.get(entity)
    if not config:
        return {"success": False, "error": f"Entity {entity} non configurée"}
    
    smtp_password = os.environ.get(config["password_env"], "")
    if not smtp_password:
        return {"success": False, "error": f"Mot de passe SMTP non configuré pour {entity}"}
    
    # Template email selon entité
    template = EMAIL_TEMPLATES.get(entity, EMAIL_TEMPLATES["ZR7"])
    
    try:
        # Date formatée pour l'objet
        date_formatted = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        
        # Créer le message
        msg = MIMEMultipart()
        msg["From"] = config["email"]
        msg["To"] = ", ".join(to_emails)
        # Objet professionnel: Livraison leads {ENTITY} – {PRODUIT} – {DATE}
        msg["Subject"] = f"Livraison leads {entity} – {produit} – {date_formatted}"
        
        # Corps du message - template professionnel par entité
        msg.attach(MIMEText(template["body"], "plain", "utf-8"))
        
        # Pièce jointe CSV (UTF-8, séparateur virgule)
        attachment = MIMEBase("text", "csv")
        attachment.set_payload(csv_content.encode("utf-8"))
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename={csv_filename}"
        )
        msg.attach(attachment)
        
        # Envoi SMTP
        with smtplib.SMTP_SSL(config["host"], config["port"], timeout=30) as server:
            server.login(config["email"], smtp_password)
            server.send_message(msg)
        
        logger.info(
            f"[CSV_SENT] entity={entity} produit={produit} "
            f"leads={lead_count} lb={lb_count} to={to_emails}"
        )
        
        return {
            "success": True,
            "emails_sent_to": to_emails,
            "lead_count": lead_count,
            "lb_count": lb_count,
            "filename": csv_filename
        }
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"[CSV_ERROR] Auth SMTP échouée pour {entity}: {str(e)}")
        return {"success": False, "error": f"Authentification SMTP échouée: {str(e)}"}
        
    except smtplib.SMTPException as e:
        logger.error(f"[CSV_ERROR] Erreur SMTP pour {entity}: {str(e)}")
        return {"success": False, "error": f"Erreur SMTP: {str(e)}"}
        
    except Exception as e:
        logger.error(f"[CSV_ERROR] Erreur inattendue: {str(e)}")
        return {"success": False, "error": str(e)}


# NOTE: deliver_to_client a été supprimé.
# Toute livraison DOIT passer par delivery_state_machine.
# Voir: daily_delivery.deliver_leads_to_client() ou routes/deliveries.py
