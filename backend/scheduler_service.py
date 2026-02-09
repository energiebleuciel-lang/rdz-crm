"""
Scheduler pour les tâches automatiques EnerSolar CRM
- Résumé quotidien à 10h
- Résumé hebdomadaire le vendredi à 10h
- Surveillance des formulaires inactifs
"""

import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("scheduler")

# Configuration DB
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'test_database')


class TaskScheduler:
    """Gestionnaire de tâches planifiées"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Europe/Paris")
        self.db_client = None
        self.db = None
        
    async def init_db(self):
        """Initialise la connexion à la base de données"""
        if not self.db_client:
            self.db_client = AsyncIOMotorClient(mongo_url)
            self.db = self.db_client[db_name]
            
    async def close_db(self):
        """Ferme la connexion à la base de données"""
        if self.db_client:
            self.db_client.close()
            
    def start(self):
        """Démarre le scheduler avec toutes les tâches"""
        # Import ici pour éviter les imports circulaires
        from email_service import email_service
        
        # Résumé quotidien à 10h (heure de Paris)
        self.scheduler.add_job(
            self.send_daily_summary,
            CronTrigger(hour=10, minute=0),
            id="daily_summary",
            name="Résumé quotidien",
            replace_existing=True
        )
        
        # Résumé hebdomadaire le vendredi à 10h
        self.scheduler.add_job(
            self.send_weekly_summary,
            CronTrigger(day_of_week="fri", hour=10, minute=0),
            id="weekly_summary",
            name="Résumé hebdomadaire",
            replace_existing=True
        )
        
        # Vérification des formulaires inactifs toutes les 6 heures
        self.scheduler.add_job(
            self.check_inactive_forms,
            CronTrigger(hour="*/6"),
            id="check_inactive_forms",
            name="Vérification formulaires inactifs",
            replace_existing=True
        )
        
        # Retry des leads échoués toutes les heures
        self.scheduler.add_job(
            self.retry_failed_leads,
            CronTrigger(minute=30),
            id="retry_failed_leads",
            name="Retry leads échoués",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler démarré avec succès")
        
    def stop(self):
        """Arrête le scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler arrêté")
            
    # ==================== TÂCHES PLANIFIÉES ====================
    
    async def send_daily_summary(self):
        """Collecte les stats et envoie le résumé quotidien"""
        from email_service import email_service
        
        try:
            await self.init_db()
            
            # Date d'hier (on envoie le résumé de la veille)
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            date_filter = {
                "created_at": {
                    "$gte": start_of_day.isoformat(),
                    "$lte": end_of_day.isoformat()
                }
            }
            
            # Stats générales
            total_leads = await self.db.leads.count_documents(date_filter)
            success = await self.db.leads.count_documents({**date_filter, "api_status": "success"})
            failed = await self.db.leads.count_documents({**date_filter, "api_status": "failed"})
            
            # Par produit
            by_product = {}
            for product in ["PV", "PAC", "ITE"]:
                count = await self.db.leads.count_documents({**date_filter, "product_type": product})
                if count > 0:
                    by_product[product] = count
            
            # Par CRM
            by_crm = {}
            pipeline = [
                {"$match": date_filter},
                {"$group": {"_id": "$target_crm_slug", "count": {"$sum": 1}}}
            ]
            async for doc in self.db.leads.aggregate(pipeline):
                crm_name = doc["_id"] or "inconnu"
                by_crm[crm_name.upper()] = doc["count"]
            
            # Top formulaires
            top_forms = []
            pipeline = [
                {"$match": date_filter},
                {"$group": {"_id": "$form_code", "leads": {"$sum": 1}}},
                {"$sort": {"leads": -1}},
                {"$limit": 5}
            ]
            async for doc in self.db.leads.aggregate(pipeline):
                top_forms.append({"name": doc["_id"] or "N/A", "leads": doc["leads"]})
            
            # Taux de conversion (form_starts -> leads)
            form_starts = await self.db.form_starts.count_documents({
                "created_at": {"$gte": start_of_day.isoformat(), "$lte": end_of_day.isoformat()}
            })
            conversion_rate = round((total_leads / form_starts * 100), 1) if form_starts > 0 else 0
            
            stats = {
                "date": yesterday.strftime("%d/%m/%Y"),
                "total_leads": total_leads,
                "success": success,
                "failed": failed,
                "by_product": by_product,
                "by_crm": by_crm,
                "conversion_rate": conversion_rate,
                "top_forms": top_forms
            }
            
            email_service.send_daily_summary(stats)
            logger.info(f"Résumé quotidien envoyé: {total_leads} leads")
            
            # Log dans la base
            await self.db.system_alerts.insert_one({
                "id": str(datetime.now(timezone.utc).timestamp()),
                "level": "INFO",
                "category": "EMAIL_SENT",
                "message": f"Résumé quotidien envoyé ({total_leads} leads)",
                "details": stats,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "resolved": True
            })
            
        except Exception as e:
            logger.error(f"Erreur résumé quotidien: {str(e)}")
            email_service.send_critical_alert(
                "SCHEDULER_ERROR",
                f"Échec de l'envoi du résumé quotidien: {str(e)}"
            )
            
    async def send_weekly_summary(self):
        """Collecte les stats et envoie le résumé hebdomadaire"""
        from email_service import email_service
        
        try:
            await self.init_db()
            
            # Semaine dernière (lundi à dimanche)
            today = datetime.now(timezone.utc)
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            
            start_of_week = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_week = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            date_filter = {
                "created_at": {
                    "$gte": start_of_week.isoformat(),
                    "$lte": end_of_week.isoformat()
                }
            }
            
            # Stats générales
            total_leads = await self.db.leads.count_documents(date_filter)
            success = await self.db.leads.count_documents({**date_filter, "api_status": "success"})
            failed = await self.db.leads.count_documents({**date_filter, "api_status": "failed"})
            success_rate = round((success / total_leads * 100), 1) if total_leads > 0 else 0
            
            # Par produit
            by_product = {}
            for product in ["PV", "PAC", "ITE"]:
                count = await self.db.leads.count_documents({**date_filter, "product_type": product})
                if count > 0:
                    by_product[product] = count
            
            # Par CRM
            by_crm = {}
            pipeline = [
                {"$match": date_filter},
                {"$group": {"_id": "$target_crm_slug", "count": {"$sum": 1}}}
            ]
            async for doc in self.db.leads.aggregate(pipeline):
                crm_name = doc["_id"] or "inconnu"
                by_crm[crm_name.upper()] = doc["count"]
            
            # Breakdown quotidien
            days_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
            daily_breakdown = []
            for i in range(7):
                day_start = start_of_week + timedelta(days=i)
                day_end = day_start.replace(hour=23, minute=59, second=59)
                count = await self.db.leads.count_documents({
                    "created_at": {"$gte": day_start.isoformat(), "$lte": day_end.isoformat()}
                })
                daily_breakdown.append({"day": days_fr[i], "leads": count})
            
            # Comparaison avec semaine précédente
            prev_start = start_of_week - timedelta(days=7)
            prev_end = end_of_week - timedelta(days=7)
            prev_total = await self.db.leads.count_documents({
                "created_at": {"$gte": prev_start.isoformat(), "$lte": prev_end.isoformat()}
            })
            
            if prev_total > 0:
                change = round(((total_leads - prev_total) / prev_total * 100), 1)
                change_str = f"+{change}%" if change >= 0 else f"{change}%"
            else:
                change_str = "+100%" if total_leads > 0 else "0%"
            
            week_num = start_of_week.isocalendar()[1]
            stats = {
                "week": f"Semaine {week_num} ({start_of_week.strftime('%d/%m')} - {end_of_week.strftime('%d/%m/%Y')})",
                "total_leads": total_leads,
                "success": success,
                "failed": failed,
                "success_rate": success_rate,
                "by_product": by_product,
                "by_crm": by_crm,
                "daily_breakdown": daily_breakdown,
                "comparison": {
                    "previous_week": prev_total,
                    "change": change_str
                }
            }
            
            email_service.send_weekly_summary(stats)
            logger.info(f"Résumé hebdomadaire envoyé: {total_leads} leads")
            
            # Log dans la base
            await self.db.system_alerts.insert_one({
                "id": str(datetime.now(timezone.utc).timestamp()),
                "level": "INFO",
                "category": "EMAIL_SENT",
                "message": f"Résumé hebdomadaire envoyé ({total_leads} leads)",
                "details": stats,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "resolved": True
            })
            
        except Exception as e:
            logger.error(f"Erreur résumé hebdomadaire: {str(e)}")
            email_service.send_critical_alert(
                "SCHEDULER_ERROR",
                f"Échec de l'envoi du résumé hebdomadaire: {str(e)}"
            )
            
    async def check_inactive_forms(self):
        """Vérifie les formulaires actifs qui n'ont pas reçu de leads récemment"""
        from email_service import email_service
        
        try:
            await self.init_db()
            
            # Formulaires actifs
            active_forms = await self.db.forms.find(
                {"status": "active"},
                {"_id": 0, "id": 1, "code": 1, "name": 1}
            ).to_list(1000)
            
            # Vérifier les leads des dernières 24h pour chaque formulaire
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            
            inactive_forms = []
            for form in active_forms:
                recent_leads = await self.db.leads.count_documents({
                    "form_code": form["code"],
                    "created_at": {"$gte": cutoff}
                })
                
                # Si un formulaire actif n'a pas reçu de leads depuis 24h
                # et qu'il en avait avant, c'est suspect
                total_leads = await self.db.leads.count_documents({"form_code": form["code"]})
                
                if total_leads > 10 and recent_leads == 0:
                    # Ce formulaire avait des leads mais plus maintenant
                    inactive_forms.append({
                        "code": form["code"],
                        "name": form.get("name", ""),
                        "total_leads": total_leads
                    })
            
            if inactive_forms:
                # Envoyer une alerte
                forms_list = ", ".join([f"{f['code']}" for f in inactive_forms[:5]])
                email_service.send_critical_alert(
                    "INACTIVE_FORMS",
                    f"{len(inactive_forms)} formulaire(s) actif(s) sans leads depuis 24h",
                    {
                        "formulaires": forms_list,
                        "action": "Vérifier si les formulaires sont encore en ligne"
                    }
                )
                
                logger.warning(f"Formulaires inactifs détectés: {len(inactive_forms)}")
            else:
                logger.info("Vérification formulaires: tout est OK")
                
        except Exception as e:
            logger.error(f"Erreur vérification formulaires: {str(e)}")
            
    async def retry_failed_leads(self):
        """Réessaye d'envoyer les leads échoués"""
        try:
            await self.init_db()
            
            # Leads échoués des dernières 24h
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            
            failed_leads = await self.db.leads.find({
                "api_status": "failed",
                "created_at": {"$gte": cutoff},
                "retry_count": {"$lt": 3}  # Max 3 tentatives
            }).to_list(50)
            
            if failed_leads:
                logger.info(f"Retry de {len(failed_leads)} leads échoués")
                
                # Marquer pour retry (le système de traitement les reprendra)
                for lead in failed_leads:
                    await self.db.leads.update_one(
                        {"id": lead["id"]},
                        {
                            "$set": {"api_status": "pending_retry"},
                            "$inc": {"retry_count": 1}
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Erreur retry leads: {str(e)}")


# Instance globale
task_scheduler = TaskScheduler()
