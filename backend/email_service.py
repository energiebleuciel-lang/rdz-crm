"""
Service d'emails SendGrid pour EnerSolar CRM
- Alertes critiques immédiates
- Résumés quotidiens (10h)
- Résumés hebdomadaires (vendredi 10h)
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger("email_service")

# Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
ALERT_EMAIL = os.environ.get('ALERT_EMAIL', 'factures.zr7digital@gmail.com')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@rdz-group-ltd.online')


class EmailService:
    """Service centralisé pour l'envoi d'emails"""
    
    def __init__(self):
        self.api_key = SENDGRID_API_KEY
        self.sender = SENDER_EMAIL
        self.alert_recipient = ALERT_EMAIL
        
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Envoie un email via SendGrid"""
        if not self.api_key:
            logger.error("SENDGRID_API_KEY non configurée")
            return False
            
        try:
            message = Mail(
                from_email=Email(self.sender, "EnerSolar CRM"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Email envoyé à {to_email}: {subject}")
                return True
            else:
                logger.error(f"Erreur envoi email: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception envoi email: {str(e)}")
            return False
    
    # ==================== ALERTES CRITIQUES ====================
    
    def send_critical_alert(self, alert_type: str, message: str, details: dict = None) -> bool:
        """
        Envoie une alerte critique immédiate.
        Types: LEAD_FAILURE, API_DOWN, SYSTEM_ERROR
        """
        subject = f"🚨 ALERTE CRITIQUE - {alert_type}"
        
        details_html = ""
        if details:
            details_html = "<ul>"
            for key, value in details.items():
                details_html += f"<li><strong>{key}:</strong> {value}</li>"
            details_html += "</ul>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: #DC2626; color: white; padding: 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .alert-box {{ background: #FEF2F2; border-left: 4px solid #DC2626; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                .details {{ background: #F3F4F6; padding: 15px; border-radius: 4px; margin-top: 20px; }}
                .footer {{ background: #F9FAFB; padding: 15px; text-align: center; font-size: 12px; color: #6B7280; }}
                .timestamp {{ color: #9CA3AF; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 ALERTE CRITIQUE</h1>
                </div>
                <div class="content">
                    <p class="timestamp">{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC</p>
                    
                    <div class="alert-box">
                        <strong>Type:</strong> {alert_type}<br>
                        <strong>Message:</strong> {message}
                    </div>
                    
                    {f'<div class="details"><strong>Détails:</strong>{details_html}</div>' if details_html else ''}
                    
                    <p style="margin-top: 30px;">
                        <strong>Action requise:</strong> Veuillez vérifier le système immédiatement.
                    </p>
                    
                    <p>
                        <a href="https://rdz-group-ltd.online" style="display: inline-block; background: #3B82F6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                            Accéder au Dashboard
                        </a>
                    </p>
                </div>
                <div class="footer">
                    EnerSolar CRM - Système d'alertes automatiques
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(self.alert_recipient, subject, html_content)
    
    # ==================== RÉSUMÉ QUOTIDIEN ====================
    
    def send_daily_summary(self, stats: dict) -> bool:
        """
        Envoie le résumé quotidien des leads.
        stats = {
            "date": "08/02/2026",
            "total_leads": 45,
            "success": 42,
            "failed": 3,
            "by_product": {"PV": 20, "PAC": 15, "ITE": 10},
            "by_crm": {"ZR7": 25, "MDL": 20},
            "conversion_rate": 12.5,
            "top_forms": [{"name": "PV-TAB-001", "leads": 15}]
        }
        """
        subject = f"📊 Résumé Quotidien - {stats.get('date', 'Aujourd\\'hui')}"
        
        # Construire les stats par produit
        products_html = ""
        for product, count in stats.get("by_product", {}).items():
            color = {"PV": "#F59E0B", "PAC": "#3B82F6", "ITE": "#10B981"}.get(product, "#6B7280")
            products_html += f'<span style="display: inline-block; background: {color}; color: white; padding: 5px 15px; border-radius: 20px; margin: 5px;">{product}: {count}</span>'
        
        # Construire les stats par CRM
        crm_html = ""
        for crm, count in stats.get("by_crm", {}).items():
            crm_html += f'<li><strong>{crm}:</strong> {count} leads</li>'
        
        # Top formulaires
        top_forms_html = ""
        for form in stats.get("top_forms", [])[:5]:
            top_forms_html += f'<li>{form.get("name", "N/A")}: {form.get("leads", 0)} leads</li>'
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #3B82F6, #1E40AF); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 10px 0 0; opacity: 0.9; }}
                .content {{ padding: 30px; }}
                .stat-grid {{ display: flex; flex-wrap: wrap; gap: 15px; margin: 20px 0; }}
                .stat-box {{ flex: 1; min-width: 120px; background: #F3F4F6; padding: 20px; border-radius: 8px; text-align: center; }}
                .stat-box .number {{ font-size: 32px; font-weight: bold; color: #1F2937; }}
                .stat-box .label {{ color: #6B7280; font-size: 14px; margin-top: 5px; }}
                .success {{ background: #D1FAE5; }}
                .success .number {{ color: #059669; }}
                .failed {{ background: #FEE2E2; }}
                .failed .number {{ color: #DC2626; }}
                .section {{ margin-top: 30px; }}
                .section h3 {{ color: #1F2937; border-bottom: 2px solid #E5E7EB; padding-bottom: 10px; }}
                .products {{ margin: 20px 0; }}
                .footer {{ background: #F9FAFB; padding: 15px; text-align: center; font-size: 12px; color: #6B7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Résumé Quotidien</h1>
                    <p>{stats.get('date', 'Aujourd\\'hui')}</p>
                </div>
                <div class="content">
                    <div class="stat-grid">
                        <div class="stat-box">
                            <div class="number">{stats.get('total_leads', 0)}</div>
                            <div class="label">Total Leads</div>
                        </div>
                        <div class="stat-box success">
                            <div class="number">{stats.get('success', 0)}</div>
                            <div class="label">Succès</div>
                        </div>
                        <div class="stat-box failed">
                            <div class="number">{stats.get('failed', 0)}</div>
                            <div class="label">Échecs</div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>📦 Par Produit</h3>
                        <div class="products">
                            {products_html if products_html else '<p style="color: #6B7280;">Aucun lead</p>'}
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>🏢 Par CRM</h3>
                        <ul>
                            {crm_html if crm_html else '<li style="color: #6B7280;">Aucune donnée</li>'}
                        </ul>
                    </div>
                    
                    <div class="section">
                        <h3>🏆 Top Formulaires</h3>
                        <ol>
                            {top_forms_html if top_forms_html else '<li style="color: #6B7280;">Aucune donnée</li>'}
                        </ol>
                    </div>
                    
                    <div style="margin-top: 30px; text-align: center;">
                        <a href="https://rdz-group-ltd.online" style="display: inline-block; background: #3B82F6; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                            Voir le Dashboard Complet
                        </a>
                    </div>
                </div>
                <div class="footer">
                    EnerSolar CRM - Résumé automatique envoyé chaque jour à 10h
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(self.alert_recipient, subject, html_content)
    
    # ==================== RÉSUMÉ HEBDOMADAIRE ====================
    
    def send_weekly_summary(self, stats: dict) -> bool:
        """
        Envoie le résumé hebdomadaire des leads.
        stats = {
            "week": "Semaine 6 (03-09/02/2026)",
            "total_leads": 312,
            "success": 298,
            "failed": 14,
            "success_rate": 95.5,
            "by_product": {"PV": 150, "PAC": 100, "ITE": 62},
            "by_crm": {"ZR7": 180, "MDL": 132},
            "daily_breakdown": [{"day": "Lundi", "leads": 45}, ...],
            "comparison": {"previous_week": 280, "change": "+11.4%"}
        }
        """
        subject = f"📈 Résumé Hebdomadaire - {stats.get('week', 'Cette semaine')}"
        
        # Stats par produit
        products_html = ""
        for product, count in stats.get("by_product", {}).items():
            color = {"PV": "#F59E0B", "PAC": "#3B82F6", "ITE": "#10B981"}.get(product, "#6B7280")
            products_html += f'''
            <div style="display: flex; align-items: center; margin: 10px 0;">
                <span style="background: {color}; color: white; padding: 5px 12px; border-radius: 4px; min-width: 50px; text-align: center;">{product}</span>
                <span style="margin-left: 15px; font-size: 18px; font-weight: bold;">{count} leads</span>
            </div>
            '''
        
        # Breakdown quotidien
        daily_html = ""
        for day_data in stats.get("daily_breakdown", []):
            bar_width = min(100, (day_data.get("leads", 0) / max(1, stats.get("total_leads", 1))) * 500)
            daily_html += f'''
            <div style="display: flex; align-items: center; margin: 8px 0;">
                <span style="min-width: 80px; color: #6B7280;">{day_data.get("day", "")}</span>
                <div style="flex: 1; background: #E5E7EB; height: 24px; border-radius: 4px; margin: 0 10px; overflow: hidden;">
                    <div style="background: #3B82F6; height: 100%; width: {bar_width}%;"></div>
                </div>
                <span style="min-width: 40px; text-align: right; font-weight: bold;">{day_data.get("leads", 0)}</span>
            </div>
            '''
        
        # Comparaison
        comparison = stats.get("comparison", {})
        change = comparison.get("change", "0%")
        change_color = "#059669" if change.startswith("+") else "#DC2626" if change.startswith("-") else "#6B7280"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #059669, #047857); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 10px 0 0; opacity: 0.9; }}
                .content {{ padding: 30px; }}
                .highlight {{ background: linear-gradient(135deg, #EEF2FF, #E0E7FF); padding: 25px; border-radius: 12px; text-align: center; margin: 20px 0; }}
                .highlight .big-number {{ font-size: 48px; font-weight: bold; color: #1E40AF; }}
                .highlight .label {{ color: #6B7280; margin-top: 5px; }}
                .stats-row {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .mini-stat {{ text-align: center; }}
                .mini-stat .value {{ font-size: 24px; font-weight: bold; }}
                .mini-stat .label {{ font-size: 12px; color: #6B7280; }}
                .section {{ margin-top: 30px; }}
                .section h3 {{ color: #1F2937; border-bottom: 2px solid #E5E7EB; padding-bottom: 10px; }}
                .comparison {{ background: #F9FAFB; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }}
                .footer {{ background: #F9FAFB; padding: 15px; text-align: center; font-size: 12px; color: #6B7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📈 Résumé Hebdomadaire</h1>
                    <p>{stats.get('week', 'Cette semaine')}</p>
                </div>
                <div class="content">
                    <div class="highlight">
                        <div class="big-number">{stats.get('total_leads', 0)}</div>
                        <div class="label">Leads cette semaine</div>
                    </div>
                    
                    <div class="stats-row">
                        <div class="mini-stat">
                            <div class="value" style="color: #059669;">{stats.get('success', 0)}</div>
                            <div class="label">Succès</div>
                        </div>
                        <div class="mini-stat">
                            <div class="value" style="color: #DC2626;">{stats.get('failed', 0)}</div>
                            <div class="label">Échecs</div>
                        </div>
                        <div class="mini-stat">
                            <div class="value" style="color: #3B82F6;">{stats.get('success_rate', 0)}%</div>
                            <div class="label">Taux de succès</div>
                        </div>
                    </div>
                    
                    <div class="comparison">
                        <div>
                            <div style="color: #6B7280; font-size: 14px;">vs semaine précédente</div>
                            <div style="font-size: 18px;">{comparison.get('previous_week', 0)} leads</div>
                        </div>
                        <div style="font-size: 24px; font-weight: bold; color: {change_color};">
                            {change}
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>📦 Par Produit</h3>
                        {products_html if products_html else '<p style="color: #6B7280;">Aucune donnée</p>'}
                    </div>
                    
                    <div class="section">
                        <h3>📅 Par Jour</h3>
                        {daily_html if daily_html else '<p style="color: #6B7280;">Aucune donnée</p>'}
                    </div>
                    
                    <div style="margin-top: 30px; text-align: center;">
                        <a href="https://rdz-group-ltd.online" style="display: inline-block; background: #059669; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                            Voir le Dashboard Complet
                        </a>
                    </div>
                </div>
                <div class="footer">
                    EnerSolar CRM - Résumé automatique envoyé chaque vendredi à 10h
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(self.alert_recipient, subject, html_content)


# Instance globale
email_service = EmailService()
