# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR FEC module for OpenERP
#    Copyright (C) 2013-2014 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'France - FEC',
    'version': '0.1',
    'category': 'French Localization',
    'license': 'AGPL-3',
    'summary': "Fichier d'Échange Informatisé (FEC) for France",
    'description': """
Fichier d'Échange Informatisé (FEC) pour la France
===================================================

Ce module permet de générer le fichier FEC tel que définit par l'arrêté du
29 Juillet 2013 portant modification des dispositions de l'article
A. 47 A-1 du livre des procédures fiscales.

Cet arrêté prévoit l'obligation pour les sociétés ayant une comptabilité
informatisée de pouvoir fournir à l'administration fiscale un fichier
regroupant l'ensemble des écritures comptables de l'exercice. Le format de ce
fichier, appelé FEC, est définit dans l'arrêté. Ce module implémente le
fichier FEC au format texte et non au format XML, car le format texte sera
facilement lisible et vérifiable par le comptable en utilisant un tableur.

Ce module a été écrit par Alexis de Lattre <alexis.delattre@akretion.com>.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': ['account_accountant'],
    'external_dependencies': {
        'python': ['unicodecsv'],
        },
    'data': [
        'wizard/fec_view.xml',
    ],
    'installable': True,
}
