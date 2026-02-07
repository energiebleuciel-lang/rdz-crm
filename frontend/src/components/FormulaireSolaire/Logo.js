import React from 'react';

// Logo officiel MaPrime-PanneauSolaire.fr - Style gouvernemental français
export const LogoMaPrimePanneauSolaire = ({ className = "", size = "default" }) => {
  const sizes = {
    small: { width: 44, height: 44, textSize: "text-sm" },
    default: { width: 56, height: 56, textSize: "text-base" },
    large: { width: 72, height: 72, textSize: "text-lg" },
  };
  
  const { width, height, textSize } = sizes[size] || sizes.default;
  
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg 
        width={width} 
        height={height} 
        viewBox="0 0 72 72" 
        fill="none" 
        xmlns="http://www.w3.org/2000/svg"
        className="flex-shrink-0"
      >
        {/* Fond bouclier officiel République Française */}
        <path
          d="M36 4L64 18V42C64 54 52 64 36 68C20 64 8 54 8 42V18L36 4Z"
          fill="url(#shield-bg)"
          stroke="#1e3a8a"
          strokeWidth="2.5"
        />
        
        {/* Bande tricolore en haut */}
        <clipPath id="shield-clip">
          <path d="M36 4L64 18V42C64 54 52 64 36 68C20 64 8 54 8 42V18L36 4Z" />
        </clipPath>
        <g clipPath="url(#shield-clip)">
          <rect x="8" y="4" width="19" height="12" fill="#002395" opacity="0.15" />
          <rect x="27" y="4" width="18" height="12" fill="white" opacity="0.3" />
          <rect x="45" y="4" width="19" height="12" fill="#ED2939" opacity="0.15" />
        </g>
        
        {/* Maison avec toit et panneaux solaires */}
        <g transform="translate(16, 20)">
          {/* Corps de la maison */}
          <path
            d="M20 14L8 24V38H16V30H24V38H32V24L20 14Z"
            fill="white"
            stroke="#1e3a8a"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          
          {/* Toit bleu */}
          <path
            d="M20 14L6 26H34L20 14Z"
            fill="#1e3a8a"
          />
          
          {/* Panneaux solaires - 6 cellules */}
          <g>
            <rect x="9" y="17" width="5" height="4" fill="#16a34a" rx="0.5" stroke="#15803d" strokeWidth="0.5" />
            <rect x="15" y="15" width="5" height="4" fill="#16a34a" rx="0.5" stroke="#15803d" strokeWidth="0.5" />
            <rect x="21" y="17" width="5" height="4" fill="#16a34a" rx="0.5" stroke="#15803d" strokeWidth="0.5" />
          </g>
          
          {/* Fenêtre/porte */}
          <rect x="17" y="30" width="6" height="8" fill="#1e3a8a" opacity="0.3" rx="1" />
        </g>
        
        {/* Soleil rayonnant */}
        <g transform="translate(50, 12)">
          <circle cx="0" cy="0" r="7" fill="#f59e0b" />
          <g stroke="#f59e0b" strokeWidth="2.5" strokeLinecap="round">
            <line x1="0" y1="-12" x2="0" y2="-9" />
            <line x1="8.5" y1="-8.5" x2="6.4" y2="-6.4" />
            <line x1="12" y1="0" x2="9" y2="0" />
            <line x1="8.5" y1="8.5" x2="6.4" y2="6.4" />
          </g>
        </g>
        
        {/* Checkmark officiel */}
        <circle cx="16" cy="56" r="8" fill="#16a34a" />
        <path d="M12 56L15 59L20 53" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        
        {/* Dégradés */}
        <defs>
          <linearGradient id="shield-bg" x1="36" y1="4" x2="36" y2="68" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#f8fafc" />
            <stop offset="50%" stopColor="#f1f5f9" />
            <stop offset="100%" stopColor="#e2e8f0" />
          </linearGradient>
        </defs>
      </svg>
      
      <div className="flex flex-col">
        <span className={`font-bold text-foreground leading-tight tracking-tight ${textSize}`}>
          MaPrime<span className="text-primary">-PanneauSolaire</span>.fr
        </span>
        <span className="text-xs text-muted-foreground font-medium">
          Simulation officielle de subvention
        </span>
      </div>
    </div>
  );
};

// Logo compact (juste l'icône)
export const LogoIcon = ({ className = "", size = 48 }) => (
  <svg 
    width={size} 
    height={size} 
    viewBox="0 0 72 72" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    {/* Fond bouclier */}
    <path
      d="M36 4L64 18V42C64 54 52 64 36 68C20 64 8 54 8 42V18L36 4Z"
      fill="url(#shield-bg-icon)"
      stroke="#1e3a8a"
      strokeWidth="2.5"
    />
    
    {/* Maison avec panneaux */}
    <g transform="translate(16, 20)">
      <path
        d="M20 14L8 24V38H16V30H24V38H32V24L20 14Z"
        fill="white"
        stroke="#1e3a8a"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path d="M20 14L6 26H34L20 14Z" fill="#1e3a8a" />
      <rect x="9" y="17" width="5" height="4" fill="#16a34a" rx="0.5" />
      <rect x="15" y="15" width="5" height="4" fill="#16a34a" rx="0.5" />
      <rect x="21" y="17" width="5" height="4" fill="#16a34a" rx="0.5" />
    </g>
    
    {/* Soleil */}
    <circle cx="50" cy="12" r="7" fill="#f59e0b" />
    
    {/* Checkmark */}
    <circle cx="16" cy="56" r="8" fill="#16a34a" />
    <path d="M12 56L15 59L20 53" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    
    <defs>
      <linearGradient id="shield-bg-icon" x1="36" y1="4" x2="36" y2="68" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#f8fafc" />
        <stop offset="100%" stopColor="#e2e8f0" />
      </linearGradient>
    </defs>
  </svg>
);

// Badges partenaires officiels
export const BadgeMaPrimeRenov = ({ className = "" }) => (
  <div className={`flex items-center gap-2 px-3 py-1.5 bg-card rounded-md shadow-sm border border-border ${className}`}>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="4" fill="#1e3a8a" />
      <path d="M7 12L10 15L17 8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
    <span className="text-xs font-medium text-muted-foreground">MaPrimeRénov'</span>
  </div>
);

export const BadgeCEE = ({ className = "" }) => (
  <div className={`flex items-center gap-2 px-3 py-1.5 bg-card rounded-md shadow-sm border border-border ${className}`}>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="4" fill="#16a34a" />
      <text x="12" y="16" textAnchor="middle" fill="white" fontSize="9" fontWeight="bold">CEE</text>
    </svg>
    <span className="text-xs font-medium text-muted-foreground">CEE</span>
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
