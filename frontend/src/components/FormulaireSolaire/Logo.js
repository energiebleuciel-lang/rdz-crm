import React from 'react';

// Logo officiel MaPrimeRénovSolaire
export const LogoMaPrimeRenovSolaire = ({ className = "", size = "default" }) => {
  const sizes = {
    small: { width: 36, height: 36, textSize: "text-xs" },
    default: { width: 48, height: 48, textSize: "text-sm" },
    large: { width: 64, height: 64, textSize: "text-base" },
  };
  
  const { width, height, textSize } = sizes[size] || sizes.default;
  
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg 
        width={width} 
        height={height} 
        viewBox="0 0 64 64" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
        className="flex-shrink-0"
      >
        {/* Fond du bouclier */}
        <path
          d="M32 4L8 14V30C8 44.36 18.12 57.52 32 60C45.88 57.52 56 44.36 56 30V14L32 4Z"
          fill="url(#shield-gradient)"
          stroke="hsl(224 64% 33%)"
          strokeWidth="2"
        />
        
        {/* Maison stylisée */}
        <path
          d="M32 18L20 27V40H26V32H38V40H44V27L32 18Z"
          fill="white"
          stroke="hsl(224 64% 33%)"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        
        {/* Toit avec panneaux solaires */}
        <path
          d="M32 18L20 27H44L32 18Z"
          fill="hsl(224 64% 33%)"
        />
        
        {/* Lignes panneaux solaires */}
        <line x1="26" y1="22" x2="30" y2="25" stroke="hsl(152 55% 45%)" strokeWidth="1.5" />
        <line x1="32" y1="20" x2="32" y2="24" stroke="hsl(152 55% 45%)" strokeWidth="1.5" />
        <line x1="38" y1="22" x2="34" y2="25" stroke="hsl(152 55% 45%)" strokeWidth="1.5" />
        
        {/* Soleil stylisé */}
        <circle cx="48" cy="20" r="6" fill="hsl(38 92% 50%)" />
        <g stroke="hsl(38 92% 50%)" strokeWidth="1.5">
          <line x1="48" y1="10" x2="48" y2="13" />
          <line x1="54" y1="14" x2="52" y2="16" />
          <line x1="56" y1="20" x2="53" y2="20" />
        </g>
        
        {/* Feuille verte (écologie) */}
        <path
          d="M16 42C16 42 18 38 22 38C22 42 18 46 16 42Z"
          fill="hsl(152 55% 45%)"
        />
        
        {/* Dégradés */}
        <defs>
          <linearGradient id="shield-gradient" x1="32" y1="4" x2="32" y2="60" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="hsl(210 50% 96%)" />
            <stop offset="100%" stopColor="hsl(210 40% 92%)" />
          </linearGradient>
        </defs>
      </svg>
      
      <div className="flex flex-col">
        <span className={`font-bold text-foreground leading-tight ${textSize}`}>
          MaPrimeRénov<span className="text-primary">Solaire</span>.fr
        </span>
        <span className="text-xs text-muted-foreground">
          Simulation de subvention
        </span>
      </div>
    </div>
  );
};

// Logo compact (juste l'icône)
export const LogoIcon = ({ className = "", size = 40 }) => (
  <svg 
    width={size} 
    height={size} 
    viewBox="0 0 64 64" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    {/* Fond du bouclier */}
    <path
      d="M32 4L8 14V30C8 44.36 18.12 57.52 32 60C45.88 57.52 56 44.36 56 30V14L32 4Z"
      fill="url(#shield-gradient-icon)"
      stroke="hsl(224 64% 33%)"
      strokeWidth="2"
    />
    
    {/* Maison stylisée */}
    <path
      d="M32 18L20 27V40H26V32H38V40H44V27L32 18Z"
      fill="white"
      stroke="hsl(224 64% 33%)"
      strokeWidth="1.5"
      strokeLinejoin="round"
    />
    
    {/* Toit avec panneaux solaires */}
    <path
      d="M32 18L20 27H44L32 18Z"
      fill="hsl(224 64% 33%)"
    />
    
    {/* Lignes panneaux solaires */}
    <line x1="26" y1="22" x2="30" y2="25" stroke="hsl(152 55% 45%)" strokeWidth="1.5" />
    <line x1="32" y1="20" x2="32" y2="24" stroke="hsl(152 55% 45%)" strokeWidth="1.5" />
    <line x1="38" y1="22" x2="34" y2="25" stroke="hsl(152 55% 45%)" strokeWidth="1.5" />
    
    {/* Soleil stylisé */}
    <circle cx="48" cy="20" r="6" fill="hsl(38 92% 50%)" />
    <g stroke="hsl(38 92% 50%)" strokeWidth="1.5">
      <line x1="48" y1="10" x2="48" y2="13" />
      <line x1="54" y1="14" x2="52" y2="16" />
      <line x1="56" y1="20" x2="53" y2="20" />
    </g>
    
    {/* Feuille verte */}
    <path
      d="M16 42C16 42 18 38 22 38C22 42 18 46 16 42Z"
      fill="hsl(152 55% 45%)"
    />
    
    <defs>
      <linearGradient id="shield-gradient-icon" x1="32" y1="4" x2="32" y2="60" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="hsl(210 50% 96%)" />
        <stop offset="100%" stopColor="hsl(210 40% 92%)" />
      </linearGradient>
    </defs>
  </svg>
);

// Badges partenaires officiels
export const BadgeMaPrimeRenov = ({ className = "" }) => (
  <div className={`flex items-center gap-2 px-3 py-1.5 bg-card rounded-md shadow-sm border border-border ${className}`}>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="4" fill="hsl(224 64% 33%)" />
      <path d="M7 12L10 15L17 8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
    <span className="text-xs font-medium text-muted-foreground">MaPrimeRénov'</span>
  </div>
);

export const BadgeCEE = ({ className = "" }) => (
  <div className={`flex items-center gap-2 px-3 py-1.5 bg-card rounded-md shadow-sm border border-border ${className}`}>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="4" fill="hsl(152 55% 45%)" />
      <text x="12" y="16" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">CEE</text>
    </svg>
    <span className="text-xs font-medium text-muted-foreground">CEE</span>
  </div>
);

export const BadgeProgrammeNational = ({ className = "" }) => (
  <div className={`flex items-center gap-2 px-3 py-1.5 bg-card rounded-md shadow-sm border border-border ${className}`}>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="8" height="24" fill="#002395" />
      <rect x="8" width="8" height="24" fill="white" />
      <rect x="16" width="8" height="24" fill="#ED2939" />
    </svg>
    <span className="text-xs font-medium text-muted-foreground hidden sm:inline">Programme National</span>
  </div>
);

export default LogoMaPrimeRenovSolaire;
