// Service API pour envoyer les leads
const API_URL = 'https://maison-du-lead.com/lead/api/create_lead/';
const API_KEY = '0c21a444-2fc9-412f-9092-658cb6d62de6';

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
 * Envoie les données du lead vers l'API
 * @param {Object} formData - Données du formulaire
 * @returns {Promise<Object>} - Réponse de l'API
 */
export const submitLead = async (formData) => {
  const timestamp = Math.floor(Date.now() / 1000);
  
  // Préparer les données selon le format API
  const leadData = {
    phone: formatPhoneNumber(formData.telephone),
    register_date: timestamp,
    nom: formData.nom || '',
    prenom: '', // Pas de prénom dans notre formulaire
    email: formData.email || '',
    custom_fields: {
      departement: { value: formData.departement || '' },
      type_logement: { value: formData.typeLogement || '' },
      statut_occupant: { value: formData.statutOccupant || '' },
      facture_electricite: { value: formData.factureElectricite || '' },
    }
  };

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Authorization': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(leadData),
    });

    const data = await response.json();
    
    // Log pour debug (à supprimer en production)
    console.log('API Response:', { status: response.status, data });

    if (response.status === 201) {
      return { success: true, message: 'Lead créé avec succès' };
    } else if (response.status === 200 && data.message?.includes('doublon')) {
      // Le lead existe déjà, mais on considère ça comme un succès côté UX
      return { success: true, message: 'Lead déjà enregistré', duplicate: true };
    } else {
      return { 
        success: false, 
        message: data.message || 'Erreur lors de la création du lead',
        status: response.status 
      };
    }
  } catch (error) {
    console.error('API Error:', error);
    return { 
      success: false, 
      message: 'Erreur de connexion au serveur',
      error: error.message 
    };
  }
};

export default submitLead;
