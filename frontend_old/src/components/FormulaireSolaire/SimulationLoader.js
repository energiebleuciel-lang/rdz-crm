import React, { useState, useEffect } from 'react';
import { Progress } from '../ui/progress';
import { Check, Shield, FileSearch, Database, Clock, Home, MapPin } from 'lucide-react';

// Configuration des simulations selon l'étape
const SIMULATION_CONFIGS = {
  logement: {
    title: "Vérification de votre logement",
    subtitle: "Analyse des critères d'éligibilité...",
    steps: [
      { id: 1, label: "Vérification du type de logement", duration: 1500, icon: Home },
      { id: 2, label: "Analyse de votre situation", duration: 1800, icon: Shield },
      { id: 3, label: "Calcul de votre consommation énergétique", duration: 2000, icon: Database },
    ]
  },
  regional: {
    title: "Simulation de vos aides régionales",
    subtitle: "Analyse des aides de votre département...",
    steps: [
      { id: 1, label: "Vérification de votre éligibilité régionale", duration: 2000, icon: Shield },
      { id: 2, label: "Analyse des aides départementales disponibles", duration: 2500, icon: MapPin },
      { id: 3, label: "Consultation de la base MaPrimeRénov'", duration: 2000, icon: Database },
    ]
  },
  final: {
    title: "Simulation de vos aides nationales",
    subtitle: "Génération de votre document personnalisé...",
    steps: [
      { id: 1, label: "Vérification de votre éligibilité nationale", duration: 1800, icon: Shield },
      { id: 2, label: "Calcul de vos subventions CEE", duration: 2200, icon: FileSearch },
      { id: 3, label: "Consultation des barèmes officiels", duration: 1800, icon: Database },
      { id: 4, label: "Estimation du montant des aides", duration: 2000, icon: Clock },
      { id: 5, label: "Génération de votre document personnalisé", duration: 2200, icon: Check },
    ]
  }
};

export const SimulationLoader = ({ onComplete, formData, type = "final" }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [stepProgress, setStepProgress] = useState(0);

  const config = SIMULATION_CONFIGS[type] || SIMULATION_CONFIGS.final;
  const steps = config.steps;

  useEffect(() => {
    let progressInterval;
    
    const runSimulation = async () => {
      for (let i = 0; i < steps.length; i++) {
        setCurrentStep(i);
        setStepProgress(0);
        
        const step = steps[i];
        const incrementPerMs = 100 / step.duration;
        
        // Animer la progression de l'étape
        await new Promise((resolve) => {
          let localProgress = 0;
          progressInterval = setInterval(() => {
            localProgress += incrementPerMs * 50;
            if (localProgress >= 100) {
              localProgress = 100;
              clearInterval(progressInterval);
              resolve();
            }
            setStepProgress(Math.min(localProgress, 100));
            // Calculer la progression globale
            const globalProgress = ((i * 100) + localProgress) / steps.length;
            setProgress(Math.min(globalProgress, 100));
          }, 50);
        });
        
        // Petite pause entre les étapes
        await new Promise(r => setTimeout(r, 300));
      }
      
      // Simulation terminée
      setTimeout(() => {
        onComplete && onComplete();
      }, 500);
    };
    
    runSimulation();
    
    return () => {
      clearInterval(progressInterval);
    };
  }, [onComplete, steps]);

  const currentStepData = steps[currentStep];
  const StepIcon = currentStepData?.icon || Shield;

  return (
    <div className="fixed inset-0 bg-background/95 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-card rounded-2xl shadow-2xl p-6 md:p-8 animate-fade-in">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-24 h-24 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4 relative">
            {/* Cercle de progression animé */}
            <svg className="absolute inset-0 w-24 h-24 -rotate-90" viewBox="0 0 96 96">
              <circle
                cx="48"
                cy="48"
                r="42"
                fill="none"
                stroke="hsl(var(--muted))"
                strokeWidth="6"
              />
              <circle
                cx="48"
                cy="48"
                r="42"
                fill="none"
                stroke="hsl(var(--primary))"
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 42}`}
                strokeDashoffset={`${2 * Math.PI * 42 * (1 - progress / 100)}`}
                className="transition-all duration-300"
              />
            </svg>
            <span className="text-3xl font-bold text-primary">
              {Math.round(progress)}%
            </span>
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-1">
            {config.title}
          </h2>
          <p className="text-sm text-muted-foreground">
            {config.subtitle}
          </p>
        </div>

        {/* Progress bar global */}
        <div className="mb-6">
          <Progress value={progress} className="h-2" />
        </div>

        {/* Liste des étapes */}
        <div className="space-y-2">
          {steps.map((step, index) => {
            const isCompleted = index < currentStep;
            const isCurrent = index === currentStep;
            const isPending = index > currentStep;
            const Icon = step.icon;

            return (
              <div
                key={step.id}
                className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-300 ${
                  isCurrent 
                    ? 'bg-primary/10 border border-primary/20' 
                    : isCompleted 
                      ? 'bg-accent-light' 
                      : 'bg-muted/30'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isCompleted 
                    ? 'bg-accent text-accent-foreground' 
                    : isCurrent 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-muted-foreground'
                }`}>
                  {isCompleted ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Icon className={`w-4 h-4 ${isCurrent ? 'animate-pulse' : ''}`} />
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium truncate ${
                    isPending ? 'text-muted-foreground' : 'text-foreground'
                  }`}>
                    {step.label}
                  </p>
                  {isCurrent && (
                    <div className="mt-1.5">
                      <div className="h-1 bg-muted rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-primary transition-all duration-100 ease-out"
                          style={{ width: `${stepProgress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {isCompleted && (
                  <span className="text-xs text-accent font-semibold">Validé</span>
                )}
              </div>
            );
          })}
        </div>

        {/* Info box avec département */}
        {formData?.departement && (
          <div className="mt-5 p-3 bg-secondary/50 rounded-lg">
            <p className="text-xs text-muted-foreground text-center">
              <span className="inline-flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                <strong className="text-foreground">Département {formData.departement}</strong>
              </span>
              {' • '}Analyse des aides en cours
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimulationLoader;
