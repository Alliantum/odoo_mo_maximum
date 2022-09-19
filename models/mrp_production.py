from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



# Here we configure the creation and modification of Manufacturing Orders
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    allow_exceed_max = fields.Boolean()
    max_allowed_reached = fields.Boolean('Max Reached')
    is_splitted_on_max = fields.Boolean()

    @api.onchange('product_qty', 'product_id')
    def onchange_check_max_raise(self):
        if not self.allow_exceed_max and self.product_id and self.product_id.max_production and self.product_uom_id and self.product_qty:
            if self.product_uom_id._compute_quantity(self.product_qty, self.product_id.uom_id) > self.product_id.max_production:
                self.max_allowed_reached = True
                return {
                    'warning': {
                        'title': 'Confirm Max Exceeded',
                        'message': _("Producing %s %s exceeds the limit of %s per a single Manufacturing Order, which is %s %s.\n\n"
                                   "If you still want to allow exceed that maximum amount for this MO, please check the field 'Allow Exceed Max'."
                                   " Otherwise a new MO will be created with the exceeded amounts.",
                                   self.product_qty, self.product_uom_id.name, self.product_id.name, self.product_id.max_production, self.product_id.uom_id.name)
                        }
                    }
        self.max_allowed_reached = False

    def _split_vals_on_max_exceeded(self, vals, product_id):
        production_uom = self.env['uom.uom'].browse(vals.get('product_uom_id'))
        product_qty_uom = production_uom._compute_quantity(vals.get('product_qty', 0.0), product_id.uom_id)
        if not product_qty_uom > product_id.max_production:
            return

        while product_qty_uom > product_id.max_production:
            yield product_id.uom_id._compute_quantity(product_id.max_production, production_uom)
            product_qty_uom = product_id.uom_id._compute_quantity(product_qty_uom - product_id.max_production, production_uom)
        yield product_id.uom_id._compute_quantity(product_qty_uom, production_uom)

    def check_max_raise(self, qty, uom_name, product_id):
        if qty > product_id.max_production:
            raise ValidationError(_(
                "Can't save this order. The amount for the MO ( %s %s ) exceeds the limit of %s per a single Manufacturing Order, which is %s %s.",
                (qty, uom_name, product_id.name, product_id.max_production, product_id.uom_id.name)
            ))

    def _find_grouping_target(self, vals, product_id=None):
        # Overridden from mrp_production_grouped_by_product module, it removes the limit on the search
        domain = self._get_grouping_target_domain(vals)
        if product_id:
            domain.append(('product_qty', '<', product_id.max_production))
        return self.env['mrp.production'].search(domain)

    def _get_next_name_by_code(self, values):
        picking_type_id = values.get('picking_type_id') or self._get_default_picking_type()
        picking_type_id = self.env['stock.picking.type'].browse(picking_type_id)
        if picking_type_id:
            return picking_type_id.sequence_id.next_by_id()
        else:
            return self.env['ir.sequence'].next_by_code('mrp.production') or _('New')

    @api.model
    def create(self, vals):
        product_id = self.env['product.product'].browse(vals.get('product_id'))

        if self.env.context.get('group_mo_by_product') and (not self.env.context.get('test_enable') or self.env.context.get('test_group_mo')):
            # this first condition seems to be for maintain compatibility with the OCA module mrp_production_grouped_by
            mo_ids = self._find_grouping_target(vals, product_id)
            product_qty = vals['product_qty']
            modified_mo_ids = self.env['mrp.production']
            for mo_id in mo_ids:
                if product_qty:
                    qty_available = product_id.max_production - mo_id.product_qty
                    if product_qty > qty_available:
                        vals['product_qty'] = qty_available
                        product_qty -= qty_available
                    else:
                        vals['product_qty'] = product_qty
                        product_qty = 0
                    mo_id.env['change.production.qty'].create({
                        'mo_id': mo_id.id,
                        'product_qty': mo_id.product_qty + vals['product_qty'],
                    }).change_prod_qty()
                    mo_id._post_mo_merging_adjustments(vals)
                    modified_mo_ids += mo_id
            # return one of the modified MO to keep consistency
            if not product_qty and modified_mo_ids:
                return modified_mo_ids[0]
            else:
                vals['product_qty'] = product_qty

        if product_id.max_production > 0 and not vals.get('allow_exceed_max'):
            procurement_group_id = vals.get('procurement_group_id', None)
            # will just iterate when really need, otherwise the loop will not be executed
            for sequence, product_qty in enumerate(self._split_vals_on_max_exceeded(vals, product_id), 1):
                new_vals = vals.copy()
                if sequence > 1 or sequence == 1 and (not vals.get('name', False) or vals['name'] == _('New')):
                    new_vals['name'] = self._get_next_name_by_code(new_vals)
                if not procurement_group_id:
                    # we just need the name for the sequence, so this will just execute in the first iteration when no given procurement group
                    procurement_group_id = self.env["procurement.group"].create(self._prepare_procurement_group_vals(new_vals)).id
                new_vals.update({
                    'backorder_sequence': sequence,
                    'product_qty': product_qty,
                    'procurement_group_id': procurement_group_id,
                    'is_splitted_on_max': True
                })
                if sequence > 1:
                    production = self.create(new_vals)
                    if not production.move_raw_ids:
                        self.env['stock.move'].sudo().create(production._get_moves_raw_values())
                    if not production.move_finished_ids:
                        self.env['stock.move'].sudo().create(production._get_moves_finished_values())
                    if not production.workorder_ids:
                        production._create_workorder()

                else:
                    vals = new_vals
        return super(MrpProduction, self.with_context(group_mo_by_product=False)).create(vals)

    def write(self, vals):
        product_id = self.env['product.product'].search([('id', '=', vals.get('product_id'))]) if 'product_id' in vals else None
        for production in self:
            if not production.allow_exceed_max:
                if not product_id: product_id = production.product_id
                allow_exceed = production.allow_exceed_max
                if 'allow_exceed_max' in vals:
                    allow_exceed = True if vals.get('allow_exceed_max') == False else False
                if product_id.max_production and product_id.max_production > 0 and not allow_exceed:
                    if 'product_qty' in vals and 'product_uom_id' in vals:
                        new_uom_id = self.env['uom.uom'].browse(vals.get('product_uom_id'))
                        qty = new_uom_id._compute_quantity(vals.get('product_qty'), product_id.uom_id)
                        production.check_max_raise(qty, new_uom_id.name, product_id)
                    elif 'product_qty' in vals:
                        qty = production.product_uom_id._compute_quantity(vals.get('product_qty'), product_id.uom_id)
                        production.check_max_raise(qty, production.product_uom_id.name, product_id)
                    elif 'product_uom_id' in vals:
                        new_uom_id = self.env['uom.uom'].browse(vals.get('product_uom_id'))
                        qty = new_uom_id._compute_quantity(production.product_qty, product_id.uom_id)
                        production.check_max_raise(qty, new_uom_id.name, product_id)
        return super(MrpProduction, self).write(vals)

    def action_confirm(self):
        for production in self.filtered(lambda p: p.move_raw_ids and p.is_splitted_on_max).mapped('procurement_group_id.mrp_production_ids'):
            self |= production
        return super(MrpProduction, self).action_confirm()
