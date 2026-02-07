import React from 'react';

// Logo simple avec drapeau français pour MaPrime-PanneauSolaire.fr
export const LogoMaPrimePanneauSolaire = ({ className = "", size = "default" }) => {
  const sizes = {
    small: { height: 32, textSize: "text-sm" },
    default: { height: 36, textSize: "text-base" },
    large: { height: 44, textSize: "text-lg" },
  };
  
  const { height, textSize } = sizes[size] || sizes.default;
  
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Drapeau français */}
      <div 
        className="flex-shrink-0 rounded overflow-hidden shadow-sm border border-border"
        style={{ width: height * 1.5, height: height }}
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
        <span className="text-xs text-muted-foreground font-medium">
          Simulation officielle
        </span>
      </div>
    </div>
  );
};

// Badges partenaires avec images externes - taille uniforme 44px de hauteur
export const BadgeMaPrimeRenov = ({ className = "" }) => (
  <div className={`flex items-center ${className}`}>
    <img 
      src="https://mes-subventions-energie.fr/wp-content/uploads/2026/02/LOGO-MPR-5.png"
      alt="MaPrimeRénov'"
      style={{ height: '44px', width: 'auto' }}
      className="object-contain"
    />
  </div>
);

export const BadgeCEE = ({ className = "" }) => (
  <div className={`flex items-center ${className}`}>
    <img 
      src="https://mes-subventions-energie.fr/wp-content/uploads/2026/02/LOGO-MPR-5-1.png-1.png"
      alt="CEE"
      style={{ height: '44px', width: 'auto' }}
      className="object-contain"
    />
  </div>
);

export default LogoMaPrimePanneauSolaire;
