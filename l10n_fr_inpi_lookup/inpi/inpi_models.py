# Copyright 2024 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel

# base inpi model


def get_role_from_code(role_code):
    role_dict = {
        "11": "Membre",
        "13": "Contrôleur de gestion",
        "14": "Contrôleur des comptes",
        "23": "Autre associé majoritaire",
        "28": "Gérant et associé indéfiniment et solidairement responsable",
        "29": "Gérant et associé indéfiniment responsable",
        "30": "Gérant",
        "40": "Liquidateur",
        "41": "Associé unique (qui participe à l’activité EURL)",
        "51": "Président du conseil d’administration",
        "52": "Président du directoire",
        "53": "Directeur Général",
        "55": "Dirigeant à l’étranger d’une personne morale étrangère",
        "56": "Dirigeant en France d’une personne morale étrangère",
        "60": "Président du conseil d’administration et directeur général",
        "61": "Président du conseil de surveillance",
        "63": "Membre du directoire",
        "64": "Membre du conseil de surveillance",
        "65": "Administrateur",
        "66": "Personne ayant le pouvoir d’engager à titre habituel la société",
        "67": "Personne ayant le pouvoir d’engager l'établissement",
        "69": "Directeur général unique de SA à directoire",
        "70": "Directeur général délégué",
        "71": "Commissaire aux comptes titulaire",
        "72": "Commissaire aux comptes suppléant",
        "73": "Président de SAS",
        "74": "Associé indéfiniment et solidairement responsable",
        "75": "Associé indéfiniment responsable",
        "76": "Représentant social d’une entreprise personne "
        "étrangère sans établissement en France",
        "77": "Représentant fiscal d’une entreprise personne étrangère "
        "sans établissement en France",
        "82": "Indivisaire",
        "86": "Exploitant pour le compte de l’indivision",
        "90": "Personne physique, exploitant en commun",
        "97": "Mandataire ad hoc",
        "98": "Administrateur provisoire",
        "99": "Autre",
        "94": "Membre non salarié participant aux travaux",
        "95": "Associé qui participe à la gestion",
        "96": "Associé non salarié",
        "100": "Repreneur",
        "101": "Entrepreneur",
        "103": "Suppléant",
        "104": "Personne chargée du contrôle",
        "105": "Personne décisionnaire désignée",
        "106": "Comptable",
        "107": "Héritier indivisaire",
        "108": "Loueur",
        "109": "Mandataire fiscal",
        "110": "Vice-Président",
        "111": "Vice-Président du Directoire",
        "120": "Vice-Président du Conseil d'Orientation et de Surveillance",
        "121": "Président du Conseil d'Orientation et de Surveillance",
        "122": "Membre du Conseil d'Orientation et de Surveillance",
        "130": "Associé unique qui récupère le patrimoine",
        "131": "Associé commandité",
        "132": "Associé commanditaire",
        "140": "Président de l'EPIC",
        "150": "Avocat",
        "200": "Fiduciaire",
        "201": "Dirigeant",
        "202": "Représentant de l'assujetti unique",
        "203": "Membre bénéficiant d'un mandat général d'administration",
        "204": "Personne capable d'engager l'entité",
        "205": "Président",
        "206": "Directeur",
        "209": "Secrétaire général",
        "210": "Membre du conseil syndical",
        "211": "Président du conseil syndical",
        "207": "Trésorier",
        "208": "Secrétaire",
        "212": "Personne désignée par les statuts",
    }

    return role_dict.get(role_code, "Not found")


class RolePourEntreprise(Enum):
    SIEGE = "1"
    SIEGE_ETS_PRIN = "2"
    ETS_PRIN = "3"
    ETS_SEC = "4"
    PREM_ETS_FRANCE = "5"
    FIRME_ETRANGERE = "6"
    SIEGE_FERME = "11"
    SIEGE_ETS_PRIN_FERME = "12"
    ETS_PRIN_FERME = "13"
    ETS_SEC_FERME = "14"
    PREM_ETS_FRANCE_FERME = "15"
    FIRME_ETRANGERE_FERME = "16"


class StatutPourFormalités(Enum):
    OUVERTURE = "1"
    FERMETURE = "2"
    MODIFIE = "3"
    REPRISE = "4"
    INCHANGE = "5"


class InpiAdresse(BaseModel):
    roleAdressePresent: bool | None = None
    roleAdresse: str | None = None
    codePostalPresent: bool | None = None
    codePostal: str | None = None
    communePresent: bool | None = None
    commune: str | None = None
    codeInseeCommunePresent: bool | None = None
    codeInseeCommune: str | None = None
    typeVoiePresent: bool | None = None
    typeVoie: str | None = None
    voiePresent: bool | None = None
    voie: str | None = None
    voieCodifieePresent: bool | None = None
    voieCodifiee: str | None = None
    numVoiePresent: bool | None = None
    numVoie: str | None = None
    indiceRepetitionPresent: bool | None = None
    indiceRepetition: str | None = None
    distributionSpecialePresent: bool | None = None
    distributionSpeciale: str | None = None
    communeAnciennePresent: bool | None = None
    communeAncienne: str | None = None
    rgpdPresent: bool | None = None
    rgpd: bool | None = None
    datePriseEffetAdressePresent: bool | None = None
    datePriseEffetAdresse: date | None = None
    complementLocalisationPresent: bool | None = None
    complementLocalisation: str | None = None
    communeDeRattachementPresent: bool | None = None
    communeDeRattachement: str | None = None
    caracteristiquesPresent: bool | None = None
    caracteristiques: dict | None = None
    indicateurValidationBANPresent: bool | None = None
    indicateurValidationBAN: str | None = None
    cedexPresent: bool | None = None
    cedex: str | None = None
    pays: str | None = None
    codePays: str | None = None


class InpiDescriptionEtablissement(BaseModel):
    rolePourEntreprise: str | None = None
    pays: str | None = None
    siret: str | None = None
    activiteNonSedentaire: bool | None = None
    sansActiviteAutreActiviteSiege: bool | None = None
    indicateurEtablissementPrincipal: bool | None = None
    statutPourFormalite: str | None = None
    etablissementValidated: bool | None = None
    etablissementRdd: bool | None = None
    dateEffet: datetime | None = None
    dateEffetFermeture: date | None = None
    dateEffetTransfert: date | None = None
    enseigne: str | None = None
    nomCommercial: str | None = None
    codeApe: str | None = None


class InpiIdentiteEntreprise(BaseModel):
    siren: str | None = None
    denomination: str | None = None
    formeJuridique: str | None = None
    nicSiege: str | None = None
    codeApe: str | None = None
    entrepriseValidated: bool | None = None
    entrepriseRdd: bool | None = None
    dateImmat: date | None = None
    origineId: str | None = None
    effectifSalarie: int | None = None
    dateDebutActiv: date | None = None


class InpiDescriptionIdentité(BaseModel):
    objet: str | None = None
    sigle: str | None = None
    duree: int | None = None
    datePremiereCloture: date | None = None
    ess: bool | None = None
    capitalVariable: bool | None = None
    montantCapital: float | None = None
    capitalMinimum: float | None = None
    deviseCapital: str | None = None
    indicateurOrigineFusionScission: bool | None = None
    indicateurAssocieUnique: bool | None = None
    depotDemandeAcre: bool | None = None
    indicateurAssocieUniqueDirigeant: bool | None = None
    natureGerance: str | None = None
    prorogationDuree: bool | None = None
    continuationAvecActifNetInferieurMoitieCapital: bool | None = None
    reconstitutionCapitauxPropres: bool | None = None


class InpiContratDAppui(BaseModel):
    adresse: InpiAdresse | None = None


class InpiActivite(BaseModel):
    categoryCode: str | None = None
    activiteId: str | None = None
    indicateurPrincipal: bool | None = None
    indicateurProlongement: bool | None = None
    dateDebut: date | None = None
    dateFin: date | None = None
    exerciceActivite: str | None = None
    indicateurNonSedentaire: bool | None = None
    formeExercice: str | None = None
    categorisationActivite1: str | None = None
    categorisationActivite2: str | None = None
    categorisationActivite3: str | None = None
    categorisationActivite4: str | None = None
    descriptionDetaillee: str | None = None
    indicateurActiviteeApe: bool | None = None
    precisionActivite: str | None = None
    indicateurArtisteAuteur: bool | None = None
    indicateurMarinProfessionnel: bool | None = None
    rolePrincipalPourEntreprise: bool | None = None
    codeApe: str | None = None
    activiteRattacheeEirl: bool | None = None
    origine: dict | None = None


class InpiPersone(BaseModel):
    sirenPresent: bool | None = None
    dateEffetRoleDeclarantPresent: bool | None = None
    dateEffetRoleDeclarant: date | None = None
    genrePresent: bool | None = None
    genre: str | None = None
    titrePresent: bool | None = None
    titre: str | None = None
    dateDeNaissancePresent: bool | None = None
    dateDeNaissance: str | None = None
    paysNaissancePresent: bool | None = None
    codePaysNaissancePresent: bool | None = None
    lieuDeNaissancePresent: bool | None = None
    codePostalNaissancePresent: bool | None = None
    codeInseeGeographiquePresent: bool | None = None
    situationMatrimonialePresent: bool | None = None
    situationMatrimoniale: str | None = None
    qualiteDeNonSedentaritePresent: bool | None = None
    qualiteDeNonSedentarite: str | None = None
    indicateurDeNonSedentaritePresent: bool | None = None
    indicateurDeNonSedentarite: bool | None = None
    role: str | None = None
    nom: str | None = None
    nomUsage: str | None = None
    prenoms: list[str] | None = []
    pseudonyme: str | None = None
    nationalite: str | None = None
    codeNationalite: str | None = None


class InpiIndividu(BaseModel):
    descriptionPersonne: InpiPersone | None = None
    adresseDomicile: InpiAdresse | None = None
    indicateurActifAgricole: bool | None = None


class InpiPouvoir(BaseModel):
    roleEntreprise: str | None = None
    typeDePersonne: str | None = None
    indicateurSecondRoleEntreprise: bool | None = None
    indicateurActifAgricole: bool | None = None
    representantId: str | None = None
    individu: InpiIndividu | None = None
    actif: bool | None = None


class InpiEtablissement(BaseModel):
    descriptionEtablissement: InpiDescriptionEtablissement | None = None
    adresse: InpiAdresse | None = None
    activites: list[InpiActivite] | None = []


class InpiAdresseEntreprise(BaseModel):
    caracteristiques: dict | None = None
    adresse: InpiAdresse | None = None
    entrepriseDomiciliataire: dict | None = None


class InpiComposition(BaseModel):
    pouvoirs: list[InpiPouvoir] | None = []


class InpiIdentitePersonneMorale(BaseModel):
    entreprise: InpiIdentiteEntreprise | None = None
    description: InpiDescriptionIdentité | None = None
    contratDAppui: InpiContratDAppui | None = None


class InpiIdentiteEntrepreneur(BaseModel):
    roleConjoint: str | None = None
    conjoint: dict | None = None
    descriptionPersonne: InpiPersone | None = None
    indicateurActifAgricole: bool | None = None
    qualiteArtisan: str | None = None


class InpiIdentitePersonnePhysique(BaseModel):
    entreprise: InpiIdentiteEntreprise | None = None
    entrepreneur: InpiIdentiteEntrepreneur | None = None
    description: InpiDescriptionIdentité | None = None
    contratDAppui: InpiContratDAppui | None = None
    contratDAppuiDeclaré: bool | None = None
    adresseCorrespondance: InpiAdresse | None = None


class InpiHistory(BaseModel):
    dateIntegration: str | None = None
    codeEvenement: str | None = None
    libelleEvenement: str | None = None
    numeroLiasse: str | None = None
    patchId: str | None = None
    dateEffet: str | None = None
    cheminDateEffet: str | None = None


class InpiPersonneMorale(BaseModel):
    adresseEntreprise: InpiAdresseEntreprise | None = None
    etablissementPrincipal: InpiEtablissement | None = None
    autresEtablissements: list[InpiEtablissement] | None = []
    composition: InpiComposition | None = None
    identite: InpiIdentitePersonneMorale | None = None
    structureEntreprise: dict | None = None
    detailCessationEntreprise: dict | None = None


class InpiPersonnePhysique(BaseModel):
    adresseEntreprise: InpiAdresseEntreprise | None = None
    etablissementPrincipal: InpiEtablissement | None = None
    autresEtablissements: list[InpiEtablissement] | None = []
    composition: InpiComposition | None = None
    identite: InpiIdentitePersonnePhysique | None = None
    structureEntreprise: dict | None = None
    detailCessationEntreprise: dict | None = None


class InpiNatureCreation(BaseModel):
    dateCreation: date | None = None
    societeEtrangere: bool | None = None
    formeJuridique: str | None = None
    typeExploitation: str | None = None
    microEntreprise: bool | None = None
    etablieEnFrance: bool | None = None
    salarieEnFrance: bool | None = None
    relieeEntrepriseAgricole: bool | None = None
    entrepriseAgricole: bool | None = None
    eirl: bool | None = None


class InpiContent(BaseModel):
    formeExerciceActivitePrincipale: str | None = None
    natureCreation: InpiNatureCreation | None = None
    personneMorale: InpiPersonneMorale | None = None
    personnePhysique: InpiPersonnePhysique | None = None
    registreAnterieur: dict | None = None
    evenementCessation: str | None = None
    natureCessation: str | None = None
    succursaleOuFiliale: str | None = None
    exploitation: InpiPersonneMorale | None = None
    piecesJointes: dict | None = None


class InpiFormality(BaseModel):
    content: InpiContent | None = None
    siren: str | None = None
    diffusionINSEE: str | None = None
    typePersonne: str | None = None
    diffusionCommerciale: bool | None = None
    historique: list[InpiHistory] | None = []
    formeJuridique: str | None = None


class InpiResponse(BaseModel):
    id: str | None = None
    siren: str | None = None
    updatedAt: datetime | None = None
    nombreRepresentantsActifs: int
    nombreEtablissementsOuverts: int
    siren: str | None = None
    formality: InpiFormality | None = None
