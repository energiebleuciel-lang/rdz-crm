import React, { useState, useCallback } from 'react';
import { Check, ChevronRight, Home, User, Phone, Mail, Zap, AlertCircle, Clock, Shield, FileText } from 'lucide-react';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';

// Liste des départements français métropolitains
const DEPARTEMENTS_FRANCE = [
  { code: '01', nom: 'Ain' },
  { code: '02', nom: 'Aisne' },
  { code: '03', nom: 'Allier' },
  { code: '04', nom: 'Alpes-de-Haute-Provence' },
  { code: '05', nom: 'Hautes-Alpes' },
  { code: '06', nom: 'Alpes-Maritimes' },
  { code: '07', nom: 'Ardèche' },
  { code: '08', nom: 'Ardennes' },
  { code: '09', nom: 'Ariège' },
  { code: '10', nom: 'Aube' },
  { code: '11', nom: 'Aude' },
  { code: '12', nom: 'Aveyron' },
  { code: '13', nom: 'Bouches-du-Rhône' },
  { code: '14', nom: 'Calvados' },
  { code: '15', nom: 'Cantal' },
  { code: '16', nom: 'Charente' },
  { code: '17', nom: 'Charente-Maritime' },
  { code: '18', nom: 'Cher' },
  { code: '19', nom: 'Corrèze' },
  { code: '2A', nom: 'Corse-du-Sud' },
  { code: '2B', nom: 'Haute-Corse' },
  { code: '21', nom: "Côte-d'Or" },
  { code: '22', nom: "Côtes-d'Armor" },
  { code: '23', nom: 'Creuse' },
  { code: '24', nom: 'Dordogne' },
  { code: '25', nom: 'Doubs' },
  { code: '26', nom: 'Drôme' },
  { code: '27', nom: 'Eure' },
  { code: '28', nom: 'Eure-et-Loir' },
  { code: '29', nom: 'Finistère' },
  { code: '30', nom: 'Gard' },
  { code: '31', nom: 'Haute-Garonne' },
  { code: '32', nom: 'Gers' },
  { code: '33', nom: 'Gironde' },
  { code: '34', nom: 'Hérault' },
  { code: '35', nom: 'Ille-et-Vilaine' },
  { code: '36', nom: 'Indre' },
  { code: '37', nom: 'Indre-et-Loire' },
  { code: '38', nom: 'Isère' },
  { code: '39', nom: 'Jura' },
  { code: '40', nom: 'Landes' },
  { code: '41', nom: 'Loir-et-Cher' },
  { code: '42', nom: 'Loire' },
  { code: '43', nom: 'Haute-Loire' },
  { code: '44', nom: 'Loire-Atlantique' },
  { code: '45', nom: 'Loiret' },
  { code: '46', nom: 'Lot' },
  { code: '47', nom: 'Lot-et-Garonne' },
  { code: '48', nom: 'Lozère' },
  { code: '49', nom: 'Maine-et-Loire' },
  { code: '50', nom: 'Manche' },
  { code: '51', nom: 'Marne' },
  { code: '52', nom: 'Haute-Marne' },
  { code: '53', nom: 'Mayenne' },
  { code: '54', nom: 'Meurthe-et-Moselle' },
  { code: '55', nom: 'Meuse' },
  { code: '56', nom: 'Morbihan' },
  { code: '57', nom: 'Moselle' },
  { code: '58', nom: 'Nièvre' },
  { code: '59', nom: 'Nord' },
  { code: '60', nom: 'Oise' },
  { code: '61', nom: 'Orne' },
  { code: '62', nom: 'Pas-de-Calais' },
  { code: '63', nom: 'Puy-de-Dôme' },
  { code: '64', nom: 'Pyrénées-Atlantiques' },
  { code: '65', nom: 'Hautes-Pyrénées' },
  { code: '66', nom: 'Pyrénées-Orientales' },
  { code: '67', nom: 'Bas-Rhin' },
  { code: '68', nom: 'Haut-Rhin' },
  { code: '69', nom: 'Rhône' },
  { code: '70', nom: 'Haute-Saône' },
  { code: '71', nom: 'Saône-et-Loire' },
  { code: '72', nom: 'Sarthe' },
  { code: '73', nom: 'Savoie' },
  { code: '74', nom: 'Haute-Savoie' },
  { code: '75', nom: 'Paris' },
  { code: '76', nom: 'Seine-Maritime' },
  { code: '77', nom: 'Seine-et-Marne' },
  { code: '78', nom: 'Yvelines' },
  { code: '79', nom: 'Deux-Sèvres' },
  { code: '80', nom: 'Somme' },
  { code: '81', nom: 'Tarn' },
  { code: '82', nom: 'Tarn-et-Garonne' },
  { code: '83', nom: 'Var' },
  { code: '84', nom: 'Vaucluse' },
  { code: '85', nom: 'Vendée' },
  { code: '86', nom: 'Vienne' },
  { code: '87', nom: 'Haute-Vienne' },
  { code: '88', nom: 'Vosges' },
  { code: '89', nom: 'Yonne' },
  { code: '90', nom: 'Territoire de Belfort' },
  { code: '91', nom: 'Essonne' },
  { code: '92', nom: 'Hauts-de-Seine' },
  { code: '93', nom: 'Seine-Saint-Denis' },
  { code: '94', nom: 'Val-de-Marne' },
  { code: '95', nom: "Val-d'Oise" },
];

const ETAPES = [
  { id: 1, titre: 'Votre logement', icon: Home },
  { id: 2, titre: 'Vos informations', icon: User },
  { id: 3, titre: 'Vos coordonnées', icon: Phone },
];

const FormulaireSolaire = () => {
  const [etapeActuelle, setEtapeActuelle] = useState(0); // 0 = intro, 1-3 = étapes
  const [formData, setFormData] = useState({
    typeLogement: '',
    statutOccupant: '',
    factureElectricite: '',
    nom: '',
    departement: '',
    email: '',
    telephone: '',
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validation du téléphone (9-10 chiffres)
  const validateTelephone = (tel) => {
    const cleaned = tel.replace(/\D/g, '');
    return cleaned.length >= 9 && cleaned.length <= 10;
  };

  // Validation du département
  const validateDepartement = (dep) => {
    return DEPARTEMENTS_FRANCE.some(d => d.code === dep);
  };

  // Gestion des changements de champs
  const handleChange = useCallback((field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  }, [errors]);

  // Validation de l'étape actuelle
  const validateEtape = useCallback(() => {
    const newErrors = {};
    
    if (etapeActuelle === 2) {
      // Étape 2: Nom et Département obligatoires
      if (!formData.nom.trim()) {
        newErrors.nom = 'Veuillez entrer votre nom';
      }
      if (!formData.departement) {
        newErrors.departement = 'Veuillez sélectionner votre département';
      } else if (!validateDepartement(formData.departement)) {
        newErrors.departement = 'Département invalide';
      }
    }
    
    if (etapeActuelle === 3) {
      // Étape 3: Téléphone obligatoire
      if (!formData.telephone.trim()) {
        newErrors.telephone = 'Veuillez entrer votre numéro de téléphone';
      } else if (!validateTelephone(formData.telephone)) {
        newErrors.telephone = 'Le numéro doit contenir entre 9 et 10 chiffres';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [etapeActuelle, formData]);

  // Passer à l'étape suivante
  const handleNextEtape = useCallback(() => {
    if (etapeActuelle === 0) {
      setEtapeActuelle(1);
      return;
    }
    
    if (validateEtape()) {
      if (etapeActuelle < 3) {
        setEtapeActuelle(prev => prev + 1);
      } else {
        // Soumettre le formulaire
        handleSubmit();
      }
    }
  }, [etapeActuelle, validateEtape]);

  // Soumission finale
  const handleSubmit = async () => {
    setIsSubmitting(true);
    
    // Simuler un délai de traitement
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Redirection vers la LP
    window.location.href = 'https://www.maprime-panneausolaire.fr/merci-outbrain/';
  };

  // Calcul du pourcentage de progression
  const progressPercent = etapeActuelle === 0 ? 0 : (etapeActuelle / 3) * 100;

  return (
    <div className="min-h-screen bg-background">
      {/* Header officiel */}
      <header className="header-banner">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-sm md:text-base font-medium">
            Plan Solaire 2026 — simulation informative et sans engagement
          </p>
        </div>
      </header>

      {/* Logos partenaires */}
      <div className="bg-card border-b border-border">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                <Home className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="font-semibold text-foreground text-sm">MaPrimeRénovSolaire.fr</p>
                <p className="text-xs text-muted-foreground">Simulation de subvention</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="logo-badge">
                <span className="text-xs font-medium text-muted-foreground">MaPrimeRénov'</span>
              </div>
              <div className="logo-badge">
                <span className="text-xs font-medium text-muted-foreground">CEE</span>
              </div>
              <div className="logo-badge hidden sm:flex">
                <span className="text-xs font-medium text-muted-foreground">Programme National</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Contenu principal */}
      <main className="max-w-2xl mx-auto px-4 py-8 md:py-12">
        {etapeActuelle === 0 ? (
          // Écran d'introduction
          <IntroScreen onStart={handleNextEtape} />
        ) : (
          // Formulaire multi-étapes
          <div className="animate-fade-in">
            {/* Indicateur de progression */}
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                {ETAPES.map((etape, index) => (
                  <div key={etape.id} className="flex items-center">
                    <div className={`step-indicator ${
                      etapeActuelle > index + 1 
                        ? 'step-indicator-completed' 
                        : etapeActuelle === index + 1 
                          ? 'step-indicator-active' 
                          : 'step-indicator-pending'
                    }`}>
                      {etapeActuelle > index + 1 ? (
                        <Check className="w-4 h-4" />
                      ) : (
                        <etape.icon className="w-4 h-4" />
                      )}
                    </div>
                    {index < ETAPES.length - 1 && (
                      <div className={`w-12 sm:w-24 h-0.5 mx-2 ${
                        etapeActuelle > index + 1 ? 'bg-accent' : 'bg-muted'
                      }`} />
                    )}
                  </div>
                ))}
              </div>
              <Progress value={progressPercent} className="h-1.5" />
              <p className="text-sm text-muted-foreground mt-2 text-center">
                Étape {etapeActuelle} sur 3 — {ETAPES[etapeActuelle - 1]?.titre}
              </p>
            </div>

            {/* Carte du formulaire */}
            <div className="form-card">
              {etapeActuelle === 1 && (
                <Etape1Logement 
                  formData={formData} 
                  onChange={handleChange} 
                  errors={errors}
                />
              )}
              {etapeActuelle === 2 && (
                <Etape2Informations 
                  formData={formData} 
                  onChange={handleChange} 
                  errors={errors}
                />
              )}
              {etapeActuelle === 3 && (
                <Etape3Coordonnees 
                  formData={formData} 
                  onChange={handleChange} 
                  errors={errors}
                  isSubmitting={isSubmitting}
                />
              )}

              {/* Bouton de navigation */}
              <div className="mt-8">
                <Button
                  onClick={handleNextEtape}
                  disabled={isSubmitting}
                  className="w-full btn-primary-gradient flex items-center justify-center gap-2 text-base"
                  size="lg"
                >
                  {isSubmitting ? (
                    <>
                      <span className="spinner" />
                      Envoi en cours...
                    </>
                  ) : (
                    <>
                      {etapeActuelle === 3 ? 'Recevoir mes résultats' : 'Continuer'}
                      <ChevronRight className="w-5 h-5" />
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card py-6">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="text-xs text-muted-foreground">
            Service gratuit et sans engagement • Vos données sont protégées et confidentielles
          </p>
        </div>
      </footer>
    </div>
  );
};

// Écran d'introduction
const IntroScreen = ({ onStart }) => (
  <div className="form-card animate-slide-up">
    <div className="text-center mb-6">
      <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
        <Home className="w-8 h-8 text-primary" />
      </div>
      <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-3">
        Bienvenue sur MaPrimeRénovSolaire
      </h1>
      <p className="text-muted-foreground">
        Ce service vous permet de vérifier si votre logement répond aux critères requis pour 
        <strong className="text-foreground"> faire partie </strong> 
        du programme solaire.
      </p>
    </div>

    <div className="bg-secondary/50 rounded-xl p-4 mb-6">
      <p className="text-sm text-foreground mb-3">
        Seuls les logements éligibles reçoivent un document détaillé, valable 6 mois.
      </p>
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-card rounded-lg flex items-center justify-center">
            <Clock className="w-4 h-4 text-primary" />
          </div>
          <span className="text-sm text-foreground">Moins d'une minute</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-card rounded-lg flex items-center justify-center">
            <Shield className="w-4 h-4 text-accent" />
          </div>
          <span className="text-sm text-foreground">Service gratuit, confidentiel et sécurisé</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-card rounded-lg flex items-center justify-center">
            <FileText className="w-4 h-4 text-primary" />
          </div>
          <span className="text-sm text-foreground">Document généré automatiquement en fin de simulation</span>
        </div>
      </div>
    </div>

    <Button
      onClick={onStart}
      className="w-full btn-primary-gradient flex items-center justify-center gap-2 text-base"
      size="lg"
    >
      Simuler ma prise en charge, montant des aides inclus
      <ChevronRight className="w-5 h-5" />
    </Button>
  </div>
);

// Étape 1: Informations sur le logement
const Etape1Logement = ({ formData, onChange, errors }) => (
  <div className="animate-slide-up space-y-6">
    <div>
      <h2 className="text-xl font-semibold text-foreground mb-2">
        Quelques informations sur votre logement
      </h2>
      <p className="text-sm text-muted-foreground">
        Ces informations sont nécessaires pour la simulation.
      </p>
    </div>

    {/* Type de logement */}
    <div>
      <label className="form-field-label">
        De quel type de propriété s'agit-il ?
      </label>
      <select
        value={formData.typeLogement}
        onChange={(e) => onChange('typeLogement', e.target.value)}
        className="select-field"
      >
        <option value="">Sélectionnez une option</option>
        <option value="maison">Maison</option>
        <option value="appartement">Appartement</option>
      </select>
      <p className="form-field-hint">
        Cette information nous permet de vérifier les critères spécifiques d'éligibilité aux aides selon le type de logement.
      </p>
    </div>

    {/* Statut occupant */}
    <div>
      <label className="form-field-label">
        Cette propriété vous appartient ?
      </label>
      <select
        value={formData.statutOccupant}
        onChange={(e) => onChange('statutOccupant', e.target.value)}
        className="select-field"
      >
        <option value="">Sélectionnez une option</option>
        <option value="proprietaire">Oui, propriétaire</option>
        <option value="locataire">Non, locataire</option>
      </select>
    </div>

    {/* Facture électricité */}
    <div>
      <label className="form-field-label">
        Quel est le montant de votre facture d'électricité mensuel ?
      </label>
      <select
        value={formData.factureElectricite}
        onChange={(e) => onChange('factureElectricite', e.target.value)}
        className="select-field"
      >
        <option value="">Sélectionnez une option</option>
        <option value="moins60">Moins de 60 €</option>
        <option value="60-100">Entre 60 € et 100 €</option>
        <option value="100-150">Entre 100 € et 150 €</option>
        <option value="plus150">Plus de 150 €</option>
      </select>
      <p className="form-field-hint">
        Selon votre dépense mensuelle en électricité, l'État peut accorder ou non des primes supplémentaires.
      </p>
    </div>
  </div>
);

// Étape 2: Informations personnelles
const Etape2Informations = ({ formData, onChange, errors }) => (
  <div className="animate-slide-up space-y-6">
    <div>
      <h2 className="text-xl font-semibold text-foreground mb-2">
        Vos aides régionales
      </h2>
      <div className="info-box mb-4">
        <p className="text-sm text-foreground">
          <strong>Votre logement est bien éligible au dispositif.</strong>
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          Nous allons maintenant analyser les aides auxquelles vous pourriez prétendre.
        </p>
      </div>
    </div>

    {/* Département */}
    <div>
      <label className="form-field-label">
        Votre département <span className="text-destructive">*</span>
      </label>
      <select
        value={formData.departement}
        onChange={(e) => onChange('departement', e.target.value)}
        className={`select-field ${errors.departement ? 'input-field-error' : ''}`}
      >
        <option value="">Sélectionnez votre département</option>
        {DEPARTEMENTS_FRANCE.map((dep) => (
          <option key={dep.code} value={dep.code}>
            {dep.code} - {dep.nom}
          </option>
        ))}
      </select>
      {errors.departement ? (
        <p className="form-field-error">
          <AlertCircle className="w-3 h-3" />
          {errors.departement}
        </p>
      ) : (
        <p className="form-field-hint">
          Il permet de savoir si l'organisme de votre département prend en charge ce programme.
        </p>
      )}
    </div>

    {/* Nom */}
    <div>
      <label className="form-field-label">
        Votre nom <span className="text-destructive">*</span>
      </label>
      <input
        type="text"
        value={formData.nom}
        onChange={(e) => onChange('nom', e.target.value)}
        placeholder="Entrez votre nom"
        className={`input-field ${errors.nom ? 'input-field-error' : ''}`}
      />
      {errors.nom ? (
        <p className="form-field-error">
          <AlertCircle className="w-3 h-3" />
          {errors.nom}
        </p>
      ) : (
        <p className="form-field-hint">
          Votre nom sert à relier votre simulation à votre profil afin de pouvoir la retrouver aisément.
        </p>
      )}
    </div>
  </div>
);

// Étape 3: Coordonnées
const Etape3Coordonnees = ({ formData, onChange, errors, isSubmitting }) => (
  <div className="animate-slide-up space-y-6">
    <div>
      <h2 className="text-xl font-semibold text-foreground mb-2">
        Vos aides nationales
      </h2>
      <div className="info-box mb-4">
        <p className="text-sm text-foreground">
          <strong>Vos aides régionales sont validées !</strong>
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          Si votre éligibilité au niveau national est confirmée, vous recevrez un 
          <strong className="text-foreground"> document récapitulant </strong> 
          toutes les aides disponibles et approuvées auxquelles vous êtes éligible.
        </p>
      </div>
    </div>

    {/* Email */}
    <div>
      <label className="form-field-label">
        Votre e-mail
      </label>
      <div className="relative">
        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="email"
          value={formData.email}
          onChange={(e) => onChange('email', e.target.value)}
          placeholder="exemple@email.com"
          className="input-field pl-10"
        />
      </div>
      <p className="form-field-hint">
        Les résultats de ce rapport reposent sur les barèmes des aides officiels qui sont actualisés quotidiennement.
      </p>
    </div>

    {/* Téléphone */}
    <div>
      <label className="form-field-label">
        Votre téléphone <span className="text-destructive">*</span>
      </label>
      <div className="relative">
        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="tel"
          value={formData.telephone}
          onChange={(e) => onChange('telephone', e.target.value)}
          placeholder="06 12 34 56 78"
          className={`input-field pl-10 ${errors.telephone ? 'input-field-error' : ''}`}
        />
      </div>
      {errors.telephone ? (
        <p className="form-field-error">
          <AlertCircle className="w-3 h-3" />
          {errors.telephone}
        </p>
      ) : (
        <p className="form-field-hint">
          Ce document est simplement informatif et n'engage à rien, il est là pour vous guider en toute tranquillité.
        </p>
      )}
    </div>

    {/* Simulation en cours */}
    {isSubmitting && (
      <div className="bg-accent-light rounded-lg p-4 mt-4">
        <div className="flex items-center gap-3">
          <div className="spinner text-accent" />
          <p className="text-sm text-foreground">
            Démarrage de la simulation de vos aides nationales...
          </p>
        </div>
        <Progress value={60} className="h-1.5 mt-3" />
      </div>
    )}
  </div>
);

export default FormulaireSolaire;
