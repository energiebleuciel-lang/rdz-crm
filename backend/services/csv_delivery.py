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

# Colonnes CSV strictes
CSV_COLUMNS = [
    "nom",
    "prenom", 
    "telephone",
    "email",
    "departement",
    "proprietaire_maison",
    "produit"
]


def generate_csv_content(leads: List[Dict], product_type: str) -> str:
    """
    Génère le contenu CSV à partir d'une liste de leads
    
    RÈGLES:
    - Seulement 7 colonnes
    - proprietaire_maison = TRUE toujours
    - produit = produit de la commande (pas du lead si LB)
    - Aucune info LB, aucun ID, aucune date
    
    Args:
        leads: Liste de documents lead
        product_type: Produit de la commande (utilisé pour tous les leads)
    
    Returns:
        Contenu CSV en string
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    
    for lead in leads:
        row = {
            "nom": lead.get("nom", ""),
            "prenom": lead.get("prenom", ""),
            "telephone": lead.get("phone", ""),
            "email": lead.get("email", ""),
            "departement": lead.get("departement", ""),
            "proprietaire_maison": "TRUE",  # Toujours TRUE
            "produit": product_type  # Produit de la COMMANDE
        }
        writer.writerow(row)
    
    return output.getvalue()


def generate_csv_filename(entity: str, client_name: str, product_type: str) -> str:
    """
    Génère un nom de fichier CSV standardisé
    Format: {ENTITY}_{CLIENT}_{PRODUIT}_{DATE}.csv
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    # Nettoyer le nom client
    clean_name = "".join(c if c.isalnum() else "_" for c in client_name)
    return f"{entity}_{clean_name}_{product_type}_{date_str}.csv"


async def send_csv_email(
    entity: str,
    to_emails: List[str],
    csv_content: str,
    csv_filename: str,
    lead_count: int,
    client_name: str,
    product_type: str
) -> Dict:
    """
    Envoie un email avec le CSV en pièce jointe
    
    Args:
        entity: ZR7 ou MDL
        to_emails: Liste des emails destinataires
        csv_content: Contenu du CSV
        csv_filename: Nom du fichier
        lead_count: Nombre de leads
        client_name: Nom du client
        product_type: Type de produit
    
    Returns:
        Dict avec status et détails
    """
    # Configuration SMTP selon entité
    smtp_config = {
        "ZR7": {
            "host": "ssl0.ovh.net",
            "port": 465,
            "email": "livraison@zr7-digital.fr",
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
    
    try:
        # Créer le message
        msg = MIMEMultipart()
        msg["From"] = config["email"]
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = f"[{entity}] Livraison {product_type} - {lead_count} leads - {client_name}"
        
        # Corps du message
        body = f"""Bonjour,

Veuillez trouver ci-joint votre livraison de leads :

- Client : {client_name}
- Produit : {product_type}
- Nombre de leads : {lead_count}
- Date : {datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")} UTC

Cordialement,
L'équipe {entity}
"""
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        # Pièce jointe CSV
        attachment = MIMEBase("text", "csv")
        attachment.set_payload(csv_content.encode("utf-8"))
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename={csv_filename}"
        )
        msg.attach(attachment)
        
        # Envoi SMTP
        with smtplib.SMTP_SSL(config["host"], config["port"]) as server:
            server.login(config["email"], smtp_password)
            server.send_message(msg)
        
        logger.info(
            f"[CSV_SENT] entity={entity} client={client_name} "
            f"leads={lead_count} to={to_emails}"
        )
        
        return {
            "success": True,
            "emails_sent_to": to_emails,
            "lead_count": lead_count
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


async def deliver_to_client(
    entity: str,
    client_id: str,
    leads: List[Dict],
    product_type: str,
    batch_id: str
) -> Dict:
    """
    Livre un batch de leads à un client
    
    1. Récupère les infos client
    2. Génère le CSV
    3. Envoie par email
    4. Met à jour les leads en base
    5. Crée le batch de livraison
    
    Args:
        entity: ZR7 ou MDL
        client_id: ID du client
        leads: Liste des leads à livrer
        product_type: Produit de la commande
        batch_id: ID du batch de livraison
    
    Returns:
        Dict avec résultat de la livraison
    """
    # 1. Récupérer le client
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        return {"success": False, "error": f"Client {client_id} non trouvé"}
    
    client_name = client.get("name", "")
    
    # Emails de livraison
    emails = [client.get("email")]
    if client.get("delivery_emails"):
        emails.extend(client.get("delivery_emails", []))
    emails = list(set(filter(None, emails)))
    
    if not emails:
        return {"success": False, "error": "Aucun email de livraison configuré"}
    
    # 2. Générer le CSV
    csv_content = generate_csv_content(leads, product_type)
    csv_filename = generate_csv_filename(entity, client_name, product_type)
    
    # 3. Envoyer par email
    send_result = await send_csv_email(
        entity=entity,
        to_emails=emails,
        csv_content=csv_content,
        csv_filename=csv_filename,
        lead_count=len(leads),
        client_name=client_name,
        product_type=product_type
    )
    
    if not send_result.get("success"):
        return send_result
    
    # 4. Mettre à jour les leads
    lead_ids = [l.get("id") for l in leads]
    now = now_iso()
    
    await db.leads.update_many(
        {"id": {"$in": lead_ids}},
        {"$set": {
            "status": "livre",
            "delivered_to_client_id": client_id,
            "delivered_to_client_name": client_name,
            "delivered_at": now,
            "delivery_method": "csv",
            "delivery_batch_id": batch_id
        }}
    )
    
    # 5. Sauvegarder le batch
    lb_count = sum(1 for lead in leads if lead.get("is_lb", False))
    
    batch = {
        "id": batch_id,
        "entity": entity,
        "client_id": client_id,
        "client_name": client_name,
        "delivery_method": "csv_email",
        "lead_ids": lead_ids,
        "lead_count": len(leads),
        "lb_count": lb_count,
        "product_type": product_type,
        "status": "sent",
        "csv_filename": csv_filename,
        "csv_emails_sent_to": emails,
        "sent_at": now,
        "created_at": now
    }
    
    await db.delivery_batches.insert_one(batch)
    
    logger.info(
        f"[DELIVERY_SUCCESS] entity={entity} client={client_name} "
        f"leads={len(leads)} lb={lb_count} batch={batch_id}"
    )
    
    return {
        "success": True,
        "batch_id": batch_id,
        "client_name": client_name,
        "lead_count": len(leads),
        "lb_count": lb_count,
        "emails_sent_to": emails
    }
