import React from 'react';

// Logo simple avec drapeau français pour MaPrime-PanneauSolaire.fr
export const LogoMaPrimePanneauSolaire = ({ className = "", size = "default" }) => {
  const sizes = {
    small: { height: 32, textSize: "text-sm" },
    default: { height: 40, textSize: "text-base" },
    large: { height: 48, textSize: "text-lg" },
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

// Badges partenaires avec images externes
export const BadgeMaPrimeRenov = ({ className = "" }) => (
  <div className={`flex items-center ${className}`}>
    <img 
      src="http://mes-subventions-energie.fr/wp-content/uploads/2026/02/LOGO-MPR-5.png"
      alt="MaPrimeRénov'"
      className="h-10 w-auto object-contain"
      onError={(e) => {
        e.target.style.display = 'none';
      }}
    />
  </div>
);

export const BadgeCEE = ({ className = "" }) => (
  <div className={`flex items-center ${className}`}>
    <img 
      src="http://mes-subventions-energie.fr/wp-content/uploads/2026/02/LOGO-MPR-5-1.png-1.png"
      alt="CEE"
      className="h-10 w-auto object-contain"
      onError={(e) => {
        e.target.style.display = 'none';
      }}
    />
  </div>
);

export const BadgeProgrammeNational = ({ className = "" }) => (
  <div className={`flex items-center gap-2 px-3 py-1.5 bg-card rounded-md shadow-sm border border-border ${className}`}>
    <svg width="24" height="16" viewBox="0 0 24 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="8" height="16" fill="#002395" />
      <rect x="8" width="8" height="16" fill="white" />
      <rect x="16" width="8" height="16" fill="#ED2939" />
      <rect x="0.5" y="0.5" width="23" height="15" stroke="#e2e8f0" strokeWidth="1" fill="none" />
    </svg>
    <span className="text-xs font-medium text-muted-foreground hidden sm:inline">Programme National</span>
  </div>
);

export default LogoMaPrimePanneauSolaire;
