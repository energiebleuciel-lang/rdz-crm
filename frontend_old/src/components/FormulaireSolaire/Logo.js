import React from 'react';

// Logo simple avec drapeau français pour MaPrime-PanneauSolaire.fr
export const LogoMaPrimePanneauSolaire = ({ className = "", size = "default" }) => {
  const sizes = {
    small: { height: 28, textSize: "text-xs" },
    default: { height: 32, textSize: "text-sm" },
    large: { height: 40, textSize: "text-base" },
  };
  
  const { height, textSize } = sizes[size] || sizes.default;
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Drapeau français */}
      <div 
        className="flex-shrink-0 rounded overflow-hidden shadow-sm border border-border"
        style={{ width: height * 1.4, height: height }}
      >
        <div className="flex h-full">
          <div className="w-1/3 h-full bg-[#002395]" />
          <div className="w-1/3 h-full bg-white" />
          <div className="w-1/3 h-full bg-[#ED2939]" />
        </div>
      </div>
      
      <div className="flex flex-col">
        <span className={`font-bold text-foreground leading-tight tracking-tight ${textSize}`}>
          MaPrime-PanneauSolaire.fr
        </span>
        <span className="text-[10px] sm:text-xs text-muted-foreground font-medium">
          Simulation d'éligibilité
        </span>
      </div>
    </div>
  );
};

// Logo partenaires (image locale) - responsive et aligné
export const LogoPartenaires = ({ className = "" }) => (
  <div className={`flex items-center flex-shrink-0 ${className}`}>
    <img 
      src="/site-independant.png"
      alt="Site indépendant - Partenaires officiels"
      className="h-8 sm:h-9 w-auto object-contain"
    />
  </div>
);

export default LogoMaPrimePanneauSolaire;
