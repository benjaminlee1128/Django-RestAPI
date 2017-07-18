# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.models import Q

import silver.models.documents.pdf
from silver.models import BillingDocumentBase


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0035_auto_20170206_0941'),
    ]

    def move_pdf_from_documents_to_model(apps, schema_editor):
        db_alias = schema_editor.connection.alias

        Invoice = apps.get_model('silver', 'Invoice')
        Proforma = apps.get_model('silver', 'Proforma')
        PDF = apps.get_model('silver', 'PDF')

        for invoice in Invoice.objects.using(db_alias).filter(
            ~Q(state=BillingDocumentBase.STATES.DRAFT)
        ):
            pdf_object = PDF.objects.using(db_alias).create(
                upload_path=invoice.get_pdf_upload_path()
            )
            pdf_object.pdf_file = invoice.pdf
            pdf_object.save(using=db_alias)

            invoice.pdf = pdf_object
            invoice.save(using=db_alias)

    def move_pdf_from_model_to_documents(apps, schema_editor):
        pass

    operations = [
        migrations.CreateModel(
            name='PDF',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pdf_file', models.FileField(upload_to=silver.models.documents.pdf.get_upload_path, null=True, editable=False, blank=True)),
                ('dirty', models.BooleanField(default=False)),
                ('upload_path', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.RenameField(
            model_name='invoice',
            old_name='pdf',
            new_name='pdf_old'
        ),
        migrations.RenameField(
            model_name='proforma',
            old_name='pdf',
            new_name='pdf_old'
        ),

        migrations.AddField(
            model_name='invoice',
            name='pdf',
            field=models.ForeignKey(to='silver.PDF', null=True),
        ),
        migrations.AddField(
            model_name='proforma',
            name='pdf',
            field=models.ForeignKey(to='silver.PDF', null=True),
        ),

        migrations.RunPython(move_pdf_from_documents_to_model,
                             move_pdf_from_model_to_documents),

        migrations.RemoveField(
            model_name='invoice',
            name='pdf_old',
        ),
        migrations.RemoveField(
            model_name='proforma',
            name='pdf_old',
        ),
        migrations.RunSQL("""
                DROP VIEW IF EXISTS silver_document;
                CREATE VIEW silver_document AS SELECT
                    'invoice' AS `kind`, id, series, number, issue_date, due_date,
                    paid_date, cancel_date, state, provider_id, customer_id,
                    proforma_id as related_document_id, archived_customer,
                    archived_provider, sales_tax_percent, sales_tax_name, currency, pdf_id,
                    transaction_currency
                    FROM silver_invoice
                UNION
                SELECT
                    'proforma' AS `kind`, id, series, number, issue_date, due_date,
                    paid_date, cancel_date, state, provider_id, customer_id,
                    NULL as related_document_id, archived_customer,
                    archived_provider, sales_tax_percent, sales_tax_name, currency, pdf_id,
                    transaction_currency
                    FROM silver_proforma WHERE invoice_id is NULL
        """),
    ]
