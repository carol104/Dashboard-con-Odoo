{
    'name': 'TechStore - Métricas de Calidad',
    'version': '16.0.1.2.0',
    'summary': 'Registro, seguimiento y análisis de pruebas de calidad',
    'description': 'Gestión de pruebas y métricas de calidad para TechStore. Registro, generador y API REST para Power BI.',
    'category': 'Productivity',
    'author': 'TechStore - Práctica académica',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/quality_groups.xml',
        'security/ir.model.access.csv',
        'data/quality_sequence.xml',
        'views/quality_test_views.xml',
        'wizard/generate_test_wizard_views.xml',
        'wizard/api_token_wizard_views.xml',
        'views/quality_menus.xml',
        'report/quality_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'practicaUnidad4/static/src/js/quality_pdf.js',
            'practicaUnidad4/static/src/xml/quality_pdf.xml',
        ],
    },
    'demo': ['demo/quality_demo.xml'],
    'application': True,
    'installable': True,
}
