Ce module permet de générer le fichier FEC tel que définit par l'arrêté du 29
Juillet 2013 portant modification des dispositions de l'article `A. 47 A-1 du
livre des procédures fiscales <https://www.legifrance.gouv.fr/affichCodeArticle.do?idArticle=LEGIARTI000018567134&cidTexte=LEGITEXT000006069583>`_.

Cet arrêté prévoit l'obligation pour les sociétés ayant une comptabilité
informatisée de pouvoir fournir à l'administration fiscale un fichier
regroupant l'ensemble des écritures comptables de l'exercice. Le format de ce
fichier, appelé *FEC*, est définit dans l'arrêté.

Le détail du format du FEC est spécifié dans le bulletin officiel des finances publiques `BOI-CF-IOR-60-40-20-20131213 <http://bofip.impots.gouv.fr/bofip/9028-PGP.html?identifiant=BOI-CF-IOR-60-40-20-20131213>` du 13 Décembre 2013. Ce module implémente le fichier
FEC au format texte et non au format XML, car le format texte sera facilement
lisible et vérifiable par le comptable en utilisant un tableur.

La structure du fichier FEC généré par ce module a été vérifiée avec le logiciel
*Test Compta Demat* version 1_00_10b disponible sur
`le site de la direction générale des finances publiques <http://www.economie.gouv.fr/dgfip/outil-test-des-fichiers-des-ecritures-comptables-fec>`
en utilisant une base de donnée Odoo réelle.

Ce module est un fork du module *l10n_fr_fec* des addons officiels. Il ajoute plusieurs options pour la génération du FEC:

* choix de l'encodage des caractères,
* choix du séparateur de champ,
* choix pour l'export du champ partenaire des lignes comptables,
* choix pour le code de partenaire.
