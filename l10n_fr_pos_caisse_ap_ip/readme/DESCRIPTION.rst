This module adds support for the **Caisse AP** protocol over IP in the Odoo Point of Sale.

The `Caisse AP protocol <https://www.associationdupaiement.fr/protocoles/protocole-caisse/>`_ is a vendor-independent protocol used in France to communicate between a point of sale and a payment terminal. It is implemented by `Ingenico <https://ingenico.com/fr/produits-et-services/terminaux-de-paiement>`_ payment terminals, `Verifone <https://www.verifone.com/>`_ payment terminal and other brands of payment terminals. This protocol is designed by a French association called `Association du paiement <https://www.associationdupaiement.fr/>`_, abbreviated as **AP**. Note that the Caisse-AP protocol is used by Ingenico payment terminals deployed in France, but not by the same model of Ingenico payment terminals deployed in other countries!

This module support a bi-directionnal link with the payment terminal:

1. it sends the amount to the payment terminal
2. it waits for the end of the payment transaction
3. it parses the answer of the payment terminal which gives the payment status: in case of success, the payment line is automatically validated ; in case of failure, an error message is displayed and the Odoo user can retry or delete the payment line.

The Caisse-AP protocol was initially written for serial and USB. Since the Caisse AP protocol version 3.x, it also supports IP. When used over IP, the client (point of sale) and the server (payment terminal) exchange simple text data encoded as ASCII over a raw TCP socket.

The Caisse-AP protocol has one important drawback: as it uses a raw TCP socket, it cannot be used from pure JS code. So the JS code of the point of sale cannot generate the query to send the amount to the payment terminal by itself. In this module, the JS code of the point of sale sends a query to the Odoo server that opens a raw TCP socket to the payment terminal. It implies that, if the Odoo server is not on the LAN but somewhere on the Internet and the payment terminal has a private IP on the LAN, you will need to setup a TCP port forwarding rule on the firewall to redirect the TCP connection of the Odoo server to the payment terminal.
