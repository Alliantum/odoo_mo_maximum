from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



# Here we configure the creation and modification of Manufacturing Orders
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    allow_exceed_max = fields.Boolean()
    max_allowed_reached = fields.Boolean('Max Reached')
    is_splitted_on_max = fields.Boolean()

    @api.model
    def create(self, vals):
        mo = super(MrpProduction, self).create(vals)
        if mo._exceeds_maximum():
            mo._create_backorders_on_max()
        return mo

    def write(self, vals):
        updated_product = vals.get('product_id') and self.env['product.product'].browse(vals['product_id'])
        updated_allow_exceed_max = vals.get('allow_exceed_max', None)

        for mo in self:
            allow_exceed_max = updated_allow_exceed_max is not None and updated_allow_exceed_max or mo.allow_exceed_max
            if not allow_exceed_max:
                product = updated_product or mo.product_id
                if product.max_production > 0:
                    if 'product_uom_id' in vals or 'product_qty' in vals:
                        product_uom_id = vals.get('product_uom_id') and self.env['uom.uom'].browse(vals['product_uom_id']) or mo.product_uom_id
                        product_qty = vals.get('product_qty', mo.product_qty)

                        if product_uom_id._compute_quantity(product_qty, product.uom_id) > product.max_production:
                            ValidationError(_(
                                "Change not allowed. The amount of %s %s exceeds the limit for %s per a single Manufacturing Order, which is %s %s.",
                                (product_qty, product_uom_id, product.name, product.max_production, product.uom_id.name)
                            ))
        return super(MrpProduction, self).write(vals)

    @api.onchange('product_qty', 'product_id')
    def onchange_check_max_raise(self):
        if self._exceeds_maximum():
            self.max_allowed_reached = True
            return {
                'warning': {
                    'title': _("Manufacturing Maximum Exceeded"),
                    'message': _(
                        "Producing %s %s exceeds the limit of %s %s for %s per a single Manufacturing Order.\n\n"
                        "If you really want to allow exceeding that maximum amount, please check the field 'Allow Exceed Max'."
                        " Otherwise a new Manufacturing Order will be created with the exceeded amounts.",
                        self.product_qty, self.product_uom_id.name, self.product_id.max_production, self.product_id.uom_id.name, self.product_id.name
                        )
                    }
                }
        self.max_allowed_reached = False

    def action_confirm(self):
        for mo in self.filtered('is_splitted_on_max').mapped('procurement_group_id.mrp_production_ids'):
            self |= mo
        return super(MrpProduction, self).action_confirm()

    def _create_backorders_on_max(self):
        exceeded_product_uom_qty = self.product_uom_qty - self.product_id.max_production
        if not self.procurement_group_id:
            self.procurement_group_id = self.env["procurement.group"].create(self._prepare_procurement_group_vals(self.read()))

        # change the original MO to product the maximum allowed
        self.env["change.production.qty"].create({
                "mo_id": self.id,
                "product_qty": self.product_id.uom_id._compute_quantity(self.product_id.max_production, self.product_uom_id),
        }).change_prod_qty()
        self.update({
            'is_splitted_on_max': True,
            'backorder_sequence': 1
        })

        for sequence, product_qty in enumerate(self._split_product_qty_max(exceeded_product_uom_qty), 2):
            backorder = self.with_context(group_mo_by_product=False).copy({
                'product_qty': product_qty,
                'is_splitted_on_max': True,
                'procurement_group_id': self.procurement_group_id.id,
                'move_raw_ids': False,
                'move_finished_ids': False,
                'finished_move_line_ids': False,
                'backorder_sequence': sequence
                # move_dest_ids
            })
            backorder._onchange_move_raw()

    def _split_product_qty_max(self, exceeded_product_uom_qty):
        product = self.product_id
        while exceeded_product_uom_qty > product.max_production:
            yield product.uom_id._compute_quantity(product.max_production, self.product_uom_id)
            exceeded_product_uom_qty -= product.max_production
        yield product.uom_id._compute_quantity(exceeded_product_uom_qty, self.product_uom_id)

    def _exceeds_maximum(self):
        if not self.allow_exceed_max and self.product_id.max_production > 0 and self.product_uom_qty > self.product_id.max_production:
            return True
        return False
