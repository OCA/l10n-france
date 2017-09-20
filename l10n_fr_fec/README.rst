.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================================================
Fichier d'Échange Informatisé (FEC) pour la France
==================================================

Ce module permet de générer le fichier FEC tel que définit par `l'arrêté du 29
Juillet 2013 <http://legifrance.gouv.fr/eli/arrete/2013/7/29/BUDE1315492A/jo/texte>`
portant modification des dispositions de l'article A. 47 A-1 du
livre des procédures fiscales.

Cet arrêté prévoit l'obligation pour les sociétés ayant une comptabilité
informatisée de pouvoir fournir à l'administration fiscale un fichier
regroupant l'ensemble des écritures comptables de l'exercice. Le format de ce
fichier, appelé *FEC*, est définit dans l'arrêté.

Le détail du format du FEC est spécifié dans le bulletin officiel des finances publiques `BOI-CF-IOR-60-40-20-20131213 <http://bofip.impots.gouv.fr/bofip/ext/pdf/createPdfWithAnnexePermalien/BOI-CF-IOR-60-40-20-20131213.pdf?doc=9028-PGP&identifiant=BOI-CF-IOR-60-40-20-20131213>` du 13 Décembre 2013. Ce module implémente le fichier
FEC au format texte et non au format XML, car le format texte sera facilement
lisible et vérifiable par le comptable en utilisant un tableur.

La structure du fichier FEC généré par ce module a été vérifiée avec le logiciel
*Test Compta Demat* version 1_00_06 disponible sur
`le site de la direction générale des finances publiques <http://www.economie.gouv.fr/dgfip/outil-test-des-fichiers-des-ecritures-comptables-fec>`
en utilisant une base de donnée Odoo réelle.

Configuration
=============

Aucune configuration n'est nécessaire.

Utilisation
===========

Pour générer le *FEC*, allez dans le menu *Accounting > Reporting > Legal
Reports > Journals > FEC* qui va démarrer l'assistant de génération du FEC.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/121/8.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/l10n-france/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Alexis de Lattre <alexis.delattre@akretion.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
