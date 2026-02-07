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

// Logo MaPrimeRénov' officiel (SVG reproduit)
export const BadgeMaPrimeRenov = ({ className = "" }) => (
  <div className={`flex items-center ${className}`}>
    <svg width="120" height="44" viewBox="0 0 120 44" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Fond */}
      <rect width="120" height="44" rx="4" fill="white"/>
      
      {/* Maison avec flèche verte */}
      <g transform="translate(8, 6)">
        {/* Maison bleue */}
        <path d="M16 8L6 16V28H12V22H20V28H26V16L16 8Z" fill="#000091"/>
        {/* Toit */}
        <path d="M16 8L4 18H28L16 8Z" fill="#000091"/>
        {/* Flèche verte montante */}
        <path d="M22 24L22 12L26 16L22 12L18 16" stroke="#1FA055" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        <path d="M22 12L26 16M22 12L18 16" stroke="#1FA055" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      </g>
      
      {/* Texte MaPrimeRénov' */}
      <text x="42" y="18" fill="#000091" fontSize="10" fontWeight="700" fontFamily="Arial, sans-serif">MaPrime</text>
      <text x="42" y="30" fill="#000091" fontSize="10" fontWeight="700" fontFamily="Arial, sans-serif">Rénov'</text>
      
      {/* Marianne stylisée */}
      <g transform="translate(95, 10)">
        <rect width="18" height="24" rx="2" fill="#000091"/>
        <text x="9" y="16" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold">RF</text>
      </g>
    </svg>
  </div>
);

// Logo CEE officiel (Certificats d'Économies d'Énergie)
export const BadgeCEE = ({ className = "" }) => (
  <div className={`flex items-center ${className}`}>
    <svg width="100" height="44" viewBox="0 0 100 44" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Fond */}
      <rect width="100" height="44" rx="4" fill="white"/>
      
      {/* Feuille/énergie verte */}
      <g transform="translate(8, 8)">
        <circle cx="14" cy="14" r="12" fill="#E8F5E9"/>
        <path d="M14 6C14 6 8 12 8 18C8 22 11 24 14 24C17 24 20 22 20 18C20 12 14 6 14 6Z" fill="#1FA055"/>
        <path d="M14 10V20M10 14H18" stroke="white" strokeWidth="2" strokeLinecap="round"/>
      </g>
      
      {/* Texte CEE */}
      <text x="40" y="20" fill="#1FA055" fontSize="14" fontWeight="700" fontFamily="Arial, sans-serif">CEE</text>
      <text x="40" y="34" fill="#666" fontSize="8" fontFamily="Arial, sans-serif">Certificats</text>
    </svg>
  </div>
);

export default LogoMaPrimePanneauSolaire;
