# -*- coding: utf-8 -*-
# Adding 'mrp_production_grouped_by_product' is just a way to ensure that our method here will be triggered before the one in the OCA module. So if not using
# the grouping module the requirement can be removed from here
{
    'name': "MO Max. Amount",
    'summary': """
        Maximum amount on MO per product""",
    'description': """
    """,
    'author': "Alliantum",
    'website': "https://www.alliantum.com",
    'category': 'Manufacturing',
    'version': '14.0.4.0.1',
    'depends': [
        'mrp',
        'stock',
        'product',
        'mrp_production_grouped_by_product' # this could be optionally removed when module not installed/used
    ],
    'data': [
        'views/product_views.xml',
        'views/mrp_production_view.xml',
        'views/change_production_view.xml',
    ]
}
