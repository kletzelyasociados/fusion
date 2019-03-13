# -*- coding: utf-8 -*-

from odoo import models, fields, api

from xml.dom import minidom
import base64
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


# class my_module(models.Model):
#     _name = 'my_module.my_module'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    UUID = fields.Text(string='Folio Fiscal')

    @api.multi
    def import_xml_data(self):

        if not self.x_xml_file:
            raise Warning('No hay ningún archivo XML adjunto!')

        else:
            # The file is stored in odoo encoded in base64 bytes column, in order to get the information in the original way
            # It must have to be decoded in the same base.
            xml = minidom.parseString(base64.b64decode(self.x_xml_file))

            # Obtengo el nodo del emisor
            emisor_items = xml.getElementsByTagName("cfdi:Emisor")

            # Obtengo los datos necesarios
            NombreEmisor = emisor_items[0].attributes['Nombre'].value
            RfcEmisor = emisor_items[0].attributes['Rfc'].value
            RegimenEmisor = emisor_items[0].attributes['RegimenFiscal'].value

            getters = Getters()

            # creo un objeto proveedor y le asigno los datos del emisor del XML
            vendor = Partner(getters.checkCompanyType(RegimenEmisor),
                             NombreEmisor,
                             RfcEmisor,
                             getters.getFiscalPosition(RegimenEmisor),
                             "85")

            # Valido que exista el proveedor
            partner_id = vendor.partnerCheck()

            # Si no existe el proveedor lo creo con los datos del XML
            if partner_id == 0:
                partner_id = vendor.createPartner()

            # Obtengo el nodo del receptor
            receptor_items = xml.getElementsByTagName("cfdi:Receptor")

            # Obtengo los datos que necesito
            NombreReceptor = receptor_items[0].attributes['Nombre'].value
            RfcReceptor = receptor_items[0].attributes['Rfc'].value
            UsoCfdi = receptor_items[0].attributes['UsoCFDI'].value

            # Obtengo el nodo del comprobante
            invoice_items = xml.getElementsByTagName("cfdi:Comprobante")

            # Obtengo los datos principales de la factura
            try:
                Serie = invoice_items[0].attributes['Serie'].value

            except:
                Serie = ""

            try:
                Folio = invoice_items[0].attributes['Folio'].value

            except:
                Folio = xml.getElementsByTagName("tfd:TimbreFiscalDigital")[0].attributes['UUID'].value

            Fecha = invoice_items[0].attributes['Fecha'].value
            FormaPago = invoice_items[0].attributes['FormaPago'].value
            SubTotal = invoice_items[0].attributes['SubTotal'].value
            Moneda = invoice_items[0].attributes['Moneda'].value
            Total = invoice_items[0].attributes['Total'].value

            # Obtengo los nodos con la información de las líneas de factura
            invoice_line_items = xml.getElementsByTagName("cfdi:Concepto")

            # Creo el Objeto interno líneas de pedido/factura
            lines = []

            try:
                self.write({'partner_id': partner_id})
            except:
                self.write({'partner_id': 2731})


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"


class Partner():

    def __init__(self, company_type, name, vat, property_account_position_id, l10n_mx_type_of_operation):
        self.partnerRow = [{
            "company_type": company_type, #person or company
            "name": name,
            "vat": vat,
            "country_id": 156, #México
            "lang": "es_MX", #Español
            "supplier": 1,
            "customer": 0,
            "property_account_position_id": property_account_position_id,
            "l10n_mx_type_of_operation": l10n_mx_type_of_operation
        }]

    @api.multi
    def createPartner(self):
        partner_id = self.env['res.partner'].create(self)
        return partner_id

    @api.multi
    def partnerCheck(self):

        try:
            print("Looking for: " + self.partnerRow[0].get("name"))
            partner_id = self.env['res.partner'].search([['name', '=', self.partnerRow[0].get("name")]], limit=1)
            return partner_id

        except:
            print("Partner not found by name")
            try:
                print("Looking by RFC: " + self.partnerRow[0].get("vat"))
                partner_id = self.env['res.partner'].search([["vat", "=", self.partnerRow[0].get("vat")]], limit=1)
                return partner_id
            except:

                return 0


class OrderLine():

    def __init__(self, product_id, name, date_planned, product_qty, product_uom, price_unit):

        self.order_line_dictionary = {
            "product_id": product_id,
            "name": name,
            "date_planned": date_planned,
            "product_qty": product_qty,
            "product_uom": product_uom,
            "price_unit": price_unit,

            #Automation in odoo to calculate taxes
            #for order_line in records:
                #order_line._compute_tax_id()
        }

        self.order_tuple = tuple((0, 1, self.order_line_dictionary))


    #FInd taxes Id desptite I am not allowed to set it by this method.


class PurchaseOrder():

    def __init__(self, state, partner_id, partner_ref, date_order, order_lines):
        self.purchase_order_dictionary = {
            "state": state,
            "partner_id": partner_id,
            "partner_ref": partner_ref,
            "date_order": date_order,
            "order_line": order_lines
        }

        self.purchase_orders_list = []

    def addPurchaseOrder(self):
        self.purchase_orders_list.append(self.purchase_order_dictionary)

    def createPurchaseOrder(self, connection):
        connection.ODOO_OBJECT.execute_kw(
            connection.DATA
            , connection.UID
            , connection.PASS
            , "purchase.order"
            , 'create'
            , self.purchase_orders_list)
        messagebox.showinfo(title="PO Creation", message="PO Created successfully!")

    """
       def _compute_tax_id(self):
           for line in self:
               fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
               # If company_id is set, always filter taxes by the company
               taxes = line.product_id.supplier_taxes_id.filtered(
                   lambda r: not line.company_id or r.company_id == line.company_id)
               line.taxes_id = fpos.map_tax(taxes, line.product_id, line.order_id.partner_id) if fpos else taxes

       def map_tax(self, taxes):
           result = taxes.browse()
           result = set()
           for tax in taxes:
               found = False
               for t in self.tax_ids:
                   if t.tax_src_id == tax:
                       result |= t.tax_dest_id
                       found = True
               if not found:
                   if t.tax_dest_id:
                       result |= t.tax_dest_id
                   break
               else:
                   result |= tax
           return result

       def onchange_product_id(self):
           result = {}
           if not self.product_id:
               return result

           # Reset date, price and quantity since _onchange_quantity will provide default values
           self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
           self.price_unit = self.product_qty = 0.0
           self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
           result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

           product_lang = self.product_id.with_context(
               lang=self.partner_id.lang,
               partner_id=self.partner_id.id,
           )
           self.name = product_lang.display_name
           if product_lang.description_purchase:
               self.name += '\n' + product_lang.description_purchase

           fpos = self.order_id.fiscal_position_id
           if self.env.uid == SUPERUSER_ID:
               company_id = self.env.user.company_id.id
               self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
           else:
               self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id)

           self._suggest_quantity()
           self._onchange_quantity()

           return result

   """  # Métodos de odoo para asignación de impuestos a lineas de PO


class InvoiceLine():

    def __init__(self, product_id, name, account_id, quantity, uom_id, price_unit):

        self.invoice_line_dictionary = {
            "product_id": product_id,
            "name": name,
            "account_id": account_id,
            "quantity": quantity,
            "uom_id": uom_id,
            "price_unit": price_unit,
            "type": "in_invoice"

        }

        self.invoice_tuple = tuple((0, 0, self.invoice_line_dictionary))


    #FInd taxes Id desptite I am not allowed to set it by this method.


class Invoice():

    def __init__(self, partner_id, reference, x_invoice_date_sat, invoice_line_ids):
        self.invoice_dictionary = {
            "partner_id": partner_id,
            "reference": reference,
            "x_invoice_date_sat": x_invoice_date_sat,
            "invoice_line_ids": invoice_line_ids,
            "type": "in_invoice"
        }

        self.invoice = []

    def addInvoice(self):
        self.invoice.append(self.invoice_dictionary)

    def createInvoice(self, connection):
        connection.ODOO_OBJECT.execute_kw(
            connection.DATA
            , connection.UID
            , connection.PASS
            , 'account.invoice'
            , 'create'
            , self.invoice)
        messagebox.showinfo(title="Invoice Creation", message="Invoice Created successfully!")


class Getters():

    @api.multi
    def checkCompanyType(self,RegimenEmisor):
        if RegimenEmisor == 612:
            return "person"
        else:
            return "company"

    @api.multi
    def getUnitOfMeasure(self, product_uom):  # Falta de adaptar

        try:

            print("Getting SAT Unit of Measure Id")
            odoo_filter = [[("code", "=", product_uom)]]
            uom_sat_id = self.connection.ODOO_OBJECT.execute_kw(
                self.connection.DATA
                , self.connection.UID
                , self.connection.PASS
                , 'l10n_mx_edi.product.sat.code'
                , 'search'
                , odoo_filter)
            print("Getting Odoo Unit of Measure Id")
            odoo_filter = [[("l10n_mx_edi_code_sat_id", "=", uom_sat_id)]]
            uom_id = self.connection.ODOO_OBJECT.execute_kw(
                self.connection.DATA
                , self.connection.UID
                , self.connection.PASS
                , 'product.uom'
                , 'search'
                , odoo_filter)

            return uom_id[0]

        except:

            return 31

    @api.multi
    def getTaxes(self, TasaoCuota, product_id):  # Falta de adaptar
        try:

            print("Getting SAT Unit of Measure Id")
            odoo_filter = [[("amount", "=", int(TasaoCuota * 10)), ("type_tax_use", "=", "Compras")]]
            tax_id = self.connection.ODOO_OBJECT.execute_kw(
                self.connection.DATA
                , self.connection.UID
                , self.connection.PASS
                , 'account.tax'
                , 'search'
                , odoo_filter)

            return tax_id

        except:

            return product_id.supplier_taxes_id

    @api.multi
    def getAccount(self, code):  # Falta de adaptar

        print("Getting Account Id")
        odoo_filter = [[("code", "=", code), ("company_id", "=", 1)]]
        account_id = self.connection.ODOO_OBJECT.execute_kw(
            self.connection.DATA
            , self.connection.UID
            , self.connection.PASS
            , 'account.account'
            , 'search'
            , odoo_filter)

        return account_id[0]

    @api.multi
    def getFiscalPosition(self, fiscal_position):

        try:

            print("Getting fiscal position")
            fiscal_position_id = self.env['account.fiscal.position'].search(
                [[("l10n_mx_edi_code", "=", fiscal_position), ("company_id", "=", 1)]], limit=1)
            return fiscal_position_id

        except:

            return 1