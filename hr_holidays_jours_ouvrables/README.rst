.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

========================
France - Jours Ouvrables
========================

Ce module permet de gérer le décompte des jours ouvrables en prenant en
compte les samedis payés. Lors de la saisie de vacances, le samedi sera
automatiquement ajouté au total des congés payés, à hauteur de 5 samedis par
an.

Référence : http://www.coindusalarie.fr/samedi-conges

Configuration
=============

Activation des jours ouvrables
------------------------------

Dans 'Configuration > Utilisateurs > Sociétés', éditer la ou les sociétés et
activer "Congés décomptés sur jours ouvrables".

Configurer le type de congé
---------------------------

Dans 'Congés > Configuration', activer les options suivantes sur le type de
congé :

* Le champ "Société" doit être saisi
* Congés décomptés sur jours ouvrables
* Exclure les jours de repos
* Exclure les jours fériés

Configurer le temps de travail
------------------------------

Dans 'Configuration > Technique > Ressource > Temps de travail', créer une
feuille de temps de travail. Celle-ci doit contenir uniquement des horaires du
lundi au vendredi.

Lier la feuille de temps aux employés.

Configurer les jours fériés
---------------------------

Dans 'Congés > Jours fériés', vous pouvez ajouter les jours fériés qui seront
exclus du décompte des congés payés.


Utilisation
===========

Le nombre de jours lors de la saisie des vacances est adapté automatiquement.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/121/10.0

Limitations
===========

Uniquement la semaine de travail du lundi au vendredi est supportée avec les
jours ouvrables à ce jour.

L'édition manuelle des samedis n'est pas encore implémentée.

Credits
=======

Contributors
------------

* Guewen Baconnier <guewen.baconnier@camptocamp.com>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
