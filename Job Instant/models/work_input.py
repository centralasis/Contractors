from odoo import fields, models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'
    _description = 'HR Work Entry Type'

    input_line_ids = fields.One2many(
        'work.entry.input', 'work_entry_id', string='Work Entry Inputs', store=True,
        readonly=False, states={'validated': [('readonly', True)], 'cancelled': [('readonly', True)], 'conflict': [('readonly', True)]})



class HrWorkEntryInput(models.Model):
    _name = 'work.entry.input'
    _description = 'work Entry Input'
    _order = 'work_entry_id, sequence'

    name = fields.Char(string="Description")
    work_entry_id = fields.Many2one('hr.work.entry', string='Work Entry', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    input_type_id = fields.Many2one('hr.payslip.input.type', string='Type', required=True, domain="['|', ('id', 'in', _allowed_input_type_ids), ('struct_ids', '=', False)]")
    _allowed_input_type_ids = fields.Many2many('hr.payslip.input.type', related='work_entry_id.contract_id.struct_id.input_line_type_ids')
    code = fields.Char(related='input_type_id.code', required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(
        string="Count")
    contract_id = fields.Many2one(
        related='work_entry_id.contract_id', string='Contract', required=True,
        help="The contract for which apply this input")
