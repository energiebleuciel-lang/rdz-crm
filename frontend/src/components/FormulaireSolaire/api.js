// Service API pour envoyer les leads via le proxy backend
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * Formate le numéro de téléphone français
 * @param {string} phone - Numéro brut
 * @returns {string} - Numéro formaté (ex: 0612345678)
 */
export const formatPhoneNumber = (phone) => {
  // Supprimer tous les caractères non numériques
  let cleaned = phone.replace(/\D/g, '');
  
  // Si le numéro commence sans le 0, l'ajouter
  if (cleaned.length === 9 && !cleaned.startsWith('0')) {
    cleaned = '0' + cleaned;
  }
  
  return cleaned;
};

/**
 * Envoie les données du lead vers l'API via le proxy backend
 * @param {Object} formData - Données du formulaire
 * @returns {Promise<Object>} - Réponse de l'API
 */
export const submitLead = async (formData) => {
  // Préparer les données
  const leadData = {
    phone: formatPhoneNumber(formData.telephone),
    nom: formData.nom || '',
    email: formData.email || '',
    departement: formData.departement || '',
    type_logement: formData.typeLogement || '',
    statut_occupant: formData.statutOccupant || '',
    facture_electricite: formData.factureElectricite || '',
  };

  console.log('Submitting lead via backend proxy:', leadData);

  try {
    const response = await fetch(`${BACKEND_URL}/api/submit-lead`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(leadData),
    });

    const data = await response.json();
    
    console.log('Lead API Response:', data);

    return data;
  } catch (error) {
    console.error('Lead API Error:', error);
    return { 
      success: false, 
      message: 'Erreur de connexion au serveur',
      error: error.message 
    };
  }
};

export default submitLead;
