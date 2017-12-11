# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR HR Expense Private Car module for OpenERP
#    Copyright (C) 2014 Akretion (http://www.akretion.com)
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
    'name': 'France - Private Car Expenses',
    'version': '0.1',
    'category': 'French Localization',
    'license': 'AGPL-3',
    'summary': "Manage private car usage in expenses for France",
    'description': """
France : Remboursement de l'utilisation d'un véhicule personnel via une note de frais
=====================================================================================

En France, quand un employé utilise son véhicule personnel dans le cadre de son travail, il peut prétendre au remboursement de frais kilométriques, à condition de bien respecter les règles en vigueur. En particulier, il faut respecter le barème de remboursement publié par l'administration, qui dépend du nombre de chevaux fiscaux et du kilométrage parcouru annuellement à titre professionnel.

Une fois le module installé, pour chaque employé qui utilise son véhicule personnel dans le cadre de son travail, vous devez renseigner sur la fiche employé, dans l'onglet *Paramètres RH*, la plaque d'immatriculation de son véhicule personnel et sélectionner l'article qui correspond au nombre de chevaux fiscaux et au kilométrage parcouru annuellement à titre professionnel. Quand l'employé créé une nouvelle note de frais, ces paramètres sont alors automatiquement renseignés à partir de sa fiche employé, et, quand il sélectionne le produit *Utilisation de mon véhicule personnel*, il est automatiquement remplacé par le bon article avec le bon prix unitaire. L'employé ne peux pas changer le prix unitaire sur la ligne de note de frais ; seul un membre du groupe *Accounting Manager* peux le faire.

Le barème kilométrique établi par l'administration a un prix au kilomètre qui a une précision au 1/10e de centimes (i.e. 3 chiffres après la virgule). Si on veut garder cette précision, il faut, AVANT d'installer ce module, aller dans le menu Configuration > Technique > Structure de la base de données > Précision décimale et mettre la précision décimale à 3 pour *Product Price*. Ensuite, il faut également appliquer un patch sur le module *product* des addons officiels :

dans le fichier addons-70/product/product.py ligne 716, dans la fonction price_get() de product.product :

CODE ORIGINAL :

if 'currency_id' in context:

CODE MODIFIE :

if 'currency_id' in context and price_type_currency_id != context['currency_id']:

puis redémarrez le serveur OpenERP. Avec ces 2 modifications, vous aurez bien la précision au 1/10e de centimes dans la notes de frais.

Ce module a été écrit par Alexis de Lattre <alexis.delattre@akretion.com>.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': ['hr_expense_onchange', 'web_context_tunnel'],
    'data': [
        'hr_employee_view.xml',
        'hr_expense_view.xml',
        'private_car_data.xml',
        'product_view.xml',
    ],
    'demo': ['private_car_demo.xml'],
    'installable': True,
}
