# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-13 10:48
from __future__ import unicode_literals

import annoying.fields
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_fsm
import silver.models.documents.base


def move_documents_to_billing_document(apps, schema_editor):
    OldInvoiceModel = apps.get_model('silver', 'Invoice')
    OldProformaModel = apps.get_model('silver', 'Proforma')

    BillingDocumentBase = apps.get_model('silver', 'BillingDocumentBase')

    db_alias = schema_editor.connection.alias

    fields_to_move = ['series', 'number', 'archived_customer', 'archived_provider', 'due_date',
                      'issue_date', 'paid_date', 'cancel_date', 'sales_tax_percent',
                      'sales_tax_name', 'currency', 'transaction_currency',
                      'transaction_xe_rate', 'transaction_xe_date', 'state', '_total',
                      '_total_in_transaction_currency', 'customer', 'pdf', 'provider']

    for old_proforma in OldProformaModel.objects.using(db_alias).filter(invoice=None):
        new_proforma = BillingDocumentBase(kind='proforma')
        for field in fields_to_move:
            setattr(new_proforma, field, getattr(old_proforma, field))
        new_proforma.save(using=db_alias)

    for old_invoice in OldInvoiceModel.objects.using(db_alias).all():
        new_invoice = BillingDocumentBase(kind='invoice')
        for field in fields_to_move:
            setattr(new_invoice, field, getattr(old_invoice, field))
        new_invoice.save(using=db_alias)

        if old_invoice.proforma:
            new_proforma = BillingDocumentBase(kind='proforma', related_document=new_invoice)
            for field in fields_to_move:
                setattr(new_proforma, field, getattr(old_invoice.proforma, field))

            new_proforma.save(using=db_alias)

            new_invoice.related_document = new_proforma
            new_invoice.save(using=db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0042_compute_totals_in_document_view'),
    ]

    operations = [
        migrations.CreateModel(
            name='BillingDocumentBase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(db_index=True, max_length=8, verbose_name=silver.models.documents.base.get_billing_documents_kinds)),
                ('series', models.CharField(blank=True, db_index=True, max_length=20, null=True)),
                ('number', models.IntegerField(blank=True, db_index=True, null=True)),
                ('archived_customer', annoying.fields.JSONField(blank=True, default=dict, null=True)),
                ('archived_provider', annoying.fields.JSONField(blank=True, default=dict, null=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('issue_date', models.DateField(blank=True, db_index=True, null=True)),
                ('paid_date', models.DateField(blank=True, null=True)),
                ('cancel_date', models.DateField(blank=True, null=True)),
                ('sales_tax_percent', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('sales_tax_name', models.CharField(blank=True, max_length=64, null=True)),
                ('currency', models.CharField(choices=[('AED', 'AED (UAE Dirham)'), ('AFN', 'AFN (Afghani)'), ('ALL', 'ALL (Lek)'), ('AMD', 'AMD (Armenian Dram)'), ('ANG', 'ANG (Netherlands Antillean Guilder)'), ('AOA', 'AOA (Kwanza)'), ('ARS', 'ARS (Argentine Peso)'), ('AUD', 'AUD (Australian Dollar)'), ('AWG', 'AWG (Aruban Florin)'), ('AZN', 'AZN (Azerbaijanian Manat)'), ('BAM', 'BAM (Convertible Mark)'), ('BBD', 'BBD (Barbados Dollar)'), ('BDT', 'BDT (Taka)'), ('BGN', 'BGN (Bulgarian Lev)'), ('BHD', 'BHD (Bahraini Dinar)'), ('BIF', 'BIF (Burundi Franc)'), ('BMD', 'BMD (Bermudian Dollar)'), ('BND', 'BND (Brunei Dollar)'), ('BOB', 'BOB (Boliviano)'), ('BRL', 'BRL (Brazilian Real)'), ('BSD', 'BSD (Bahamian Dollar)'), ('BTN', 'BTN (Ngultrum)'), ('BWP', 'BWP (Pula)'), ('BYN', 'BYN (Belarusian Ruble)'), ('BZD', 'BZD (Belize Dollar)'), ('CAD', 'CAD (Canadian Dollar)'), ('CDF', 'CDF (Congolese Franc)'), ('CHF', 'CHF (Swiss Franc)'), ('CLP', 'CLP (Chilean Peso)'), ('CNY', 'CNY (Yuan Renminbi)'), ('COP', 'COP (Colombian Peso)'), ('CRC', 'CRC (Costa Rican Colon)'), ('CUC', 'CUC (Peso Convertible)'), ('CUP', 'CUP (Cuban Peso)'), ('CVE', 'CVE (Cabo Verde Escudo)'), ('CZK', 'CZK (Czech Koruna)'), ('DJF', 'DJF (Djibouti Franc)'), ('DKK', 'DKK (Danish Krone)'), ('DOP', 'DOP (Dominican Peso)'), ('DZD', 'DZD (Algerian Dinar)'), ('EGP', 'EGP (Egyptian Pound)'), ('ERN', 'ERN (Nakfa)'), ('ETB', 'ETB (Ethiopian Birr)'), ('EUR', 'EUR (Euro)'), ('FJD', 'FJD (Fiji Dollar)'), ('FKP', 'FKP (Falkland Islands Pound)'), ('GBP', 'GBP (Pound Sterling)'), ('GEL', 'GEL (Lari)'), ('GHS', 'GHS (Ghana Cedi)'), ('GIP', 'GIP (Gibraltar Pound)'), ('GMD', 'GMD (Dalasi)'), ('GNF', 'GNF (Guinea Franc)'), ('GTQ', 'GTQ (Quetzal)'), ('GYD', 'GYD (Guyana Dollar)'), ('HKD', 'HKD (Hong Kong Dollar)'), ('HNL', 'HNL (Lempira)'), ('HRK', 'HRK (Kuna)'), ('HTG', 'HTG (Gourde)'), ('HUF', 'HUF (Forint)'), ('IDR', 'IDR (Rupiah)'), ('ILS', 'ILS (New Israeli Sheqel)'), ('INR', 'INR (Indian Rupee)'), ('IQD', 'IQD (Iraqi Dinar)'), ('IRR', 'IRR (Iranian Rial)'), ('ISK', 'ISK (Iceland Krona)'), ('JMD', 'JMD (Jamaican Dollar)'), ('JOD', 'JOD (Jordanian Dinar)'), ('JPY', 'JPY (Yen)'), ('KES', 'KES (Kenyan Shilling)'), ('KGS', 'KGS (Som)'), ('KHR', 'KHR (Riel)'), ('KMF', 'KMF (Comoro Franc)'), ('KPW', 'KPW (North Korean Won)'), ('KRW', 'KRW (Won)'), ('KWD', 'KWD (Kuwaiti Dinar)'), ('KYD', 'KYD (Cayman Islands Dollar)'), ('KZT', 'KZT (Tenge)'), ('LAK', 'LAK (Kip)'), ('LBP', 'LBP (Lebanese Pound)'), ('LKR', 'LKR (Sri Lanka Rupee)'), ('LRD', 'LRD (Liberian Dollar)'), ('LSL', 'LSL (Loti)'), ('LYD', 'LYD (Libyan Dinar)'), ('MAD', 'MAD (Moroccan Dirham)'), ('MDL', 'MDL (Moldovan Leu)'), ('MGA', 'MGA (Malagasy Ariary)'), ('MKD', 'MKD (Denar)'), ('MMK', 'MMK (Kyat)'), ('MNT', 'MNT (Tugrik)'), ('MOP', 'MOP (Pataca)'), ('MRO', 'MRO (Ouguiya)'), ('MUR', 'MUR (Mauritius Rupee)'), ('MVR', 'MVR (Rufiyaa)'), ('MWK', 'MWK (Malawi Kwacha)'), ('MXN', 'MXN (Mexican Peso)'), ('MYR', 'MYR (Malaysian Ringgit)'), ('MZN', 'MZN (Mozambique Metical)'), ('NAD', 'NAD (Namibia Dollar)'), ('NGN', 'NGN (Naira)'), ('NIO', 'NIO (Cordoba Oro)'), ('NOK', 'NOK (Norwegian Krone)'), ('NPR', 'NPR (Nepalese Rupee)'), ('NZD', 'NZD (New Zealand Dollar)'), ('OMR', 'OMR (Rial Omani)'), ('PAB', 'PAB (Balboa)'), ('PEN', 'PEN (Sol)'), ('PGK', 'PGK (Kina)'), ('PHP', 'PHP (Philippine Peso)'), ('PKR', 'PKR (Pakistan Rupee)'), ('PLN', 'PLN (Zloty)'), ('PYG', 'PYG (Guarani)'), ('QAR', 'QAR (Qatari Rial)'), ('RON', 'RON (Romanian Leu)'), ('RSD', 'RSD (Serbian Dinar)'), ('RUB', 'RUB (Russian Ruble)'), ('RWF', 'RWF (Rwanda Franc)'), ('SAR', 'SAR (Saudi Riyal)'), ('SBD', 'SBD (Solomon Islands Dollar)'), ('SCR', 'SCR (Seychelles Rupee)'), ('SDG', 'SDG (Sudanese Pound)'), ('SEK', 'SEK (Swedish Krona)'), ('SGD', 'SGD (Singapore Dollar)'), ('SHP', 'SHP (Saint Helena Pound)'), ('SLL', 'SLL (Leone)'), ('SOS', 'SOS (Somali Shilling)'), ('SRD', 'SRD (Surinam Dollar)'), ('SSP', 'SSP (South Sudanese Pound)'), ('STD', 'STD (Dobra)'), ('SVC', 'SVC (El Salvador Colon)'), ('SYP', 'SYP (Syrian Pound)'), ('SZL', 'SZL (Lilangeni)'), ('THB', 'THB (Baht)'), ('TJS', 'TJS (Somoni)'), ('TMT', 'TMT (Turkmenistan New Manat)'), ('TND', 'TND (Tunisian Dinar)'), ('TOP', 'TOP (Pa\u2019anga)'), ('TRY', 'TRY (Turkish Lira)'), ('TTD', 'TTD (Trinidad and Tobago Dollar)'), ('TWD', 'TWD (New Taiwan Dollar)'), ('TZS', 'TZS (Tanzanian Shilling)'), ('UAH', 'UAH (Hryvnia)'), ('UGX', 'UGX (Uganda Shilling)'), ('USD', 'USD (US Dollar)'), ('UYU', 'UYU (Peso Uruguayo)'), ('UZS', 'UZS (Uzbekistan Sum)'), ('VEF', 'VEF (Bol\xedvar)'), ('VND', 'VND (Dong)'), ('VUV', 'VUV (Vatu)'), ('WST', 'WST (Tala)'), ('XAF', 'XAF (CFA Franc BEAC)'), ('XAG', 'XAG (Silver)'), ('XAU', 'XAU (Gold)'), ('XBA', 'XBA (Bond Markets Unit European Composite Unit (EURCO))'), ('XBB', 'XBB (Bond Markets Unit European Monetary Unit (E.M.U.-6))'), ('XBC', 'XBC (Bond Markets Unit European Unit of Account 9 (E.U.A.-9))'), ('XBD', 'XBD (Bond Markets Unit European Unit of Account 17 (E.U.A.-17))'), ('XCD', 'XCD (East Caribbean Dollar)'), ('XDR', 'XDR (SDR (Special Drawing Right))'), ('XOF', 'XOF (CFA Franc BCEAO)'), ('XPD', 'XPD (Palladium)'), ('XPF', 'XPF (CFP Franc)'), ('XPT', 'XPT (Platinum)'), ('XSU', 'XSU (Sucre)'), ('XTS', 'XTS (Codes specifically reserved for testing purposes)'), ('XUA', 'XUA (ADB Unit of Account)'), ('XXX', 'XXX (The codes assigned for transactions where no currency is involved)'), ('YER', 'YER (Yemeni Rial)'), ('ZAR', 'ZAR (Rand)'), ('ZMW', 'ZMW (Zambian Kwacha)'), ('ZWL', 'ZWL (Zimbabwe Dollar)')], default=b'USD', help_text=b'The currency used for billing.', max_length=4)),
                ('transaction_currency', models.CharField(choices=[('AED', 'AED (UAE Dirham)'), ('AFN', 'AFN (Afghani)'), ('ALL', 'ALL (Lek)'), ('AMD', 'AMD (Armenian Dram)'), ('ANG', 'ANG (Netherlands Antillean Guilder)'), ('AOA', 'AOA (Kwanza)'), ('ARS', 'ARS (Argentine Peso)'), ('AUD', 'AUD (Australian Dollar)'), ('AWG', 'AWG (Aruban Florin)'), ('AZN', 'AZN (Azerbaijanian Manat)'), ('BAM', 'BAM (Convertible Mark)'), ('BBD', 'BBD (Barbados Dollar)'), ('BDT', 'BDT (Taka)'), ('BGN', 'BGN (Bulgarian Lev)'), ('BHD', 'BHD (Bahraini Dinar)'), ('BIF', 'BIF (Burundi Franc)'), ('BMD', 'BMD (Bermudian Dollar)'), ('BND', 'BND (Brunei Dollar)'), ('BOB', 'BOB (Boliviano)'), ('BRL', 'BRL (Brazilian Real)'), ('BSD', 'BSD (Bahamian Dollar)'), ('BTN', 'BTN (Ngultrum)'), ('BWP', 'BWP (Pula)'), ('BYN', 'BYN (Belarusian Ruble)'), ('BZD', 'BZD (Belize Dollar)'), ('CAD', 'CAD (Canadian Dollar)'), ('CDF', 'CDF (Congolese Franc)'), ('CHF', 'CHF (Swiss Franc)'), ('CLP', 'CLP (Chilean Peso)'), ('CNY', 'CNY (Yuan Renminbi)'), ('COP', 'COP (Colombian Peso)'), ('CRC', 'CRC (Costa Rican Colon)'), ('CUC', 'CUC (Peso Convertible)'), ('CUP', 'CUP (Cuban Peso)'), ('CVE', 'CVE (Cabo Verde Escudo)'), ('CZK', 'CZK (Czech Koruna)'), ('DJF', 'DJF (Djibouti Franc)'), ('DKK', 'DKK (Danish Krone)'), ('DOP', 'DOP (Dominican Peso)'), ('DZD', 'DZD (Algerian Dinar)'), ('EGP', 'EGP (Egyptian Pound)'), ('ERN', 'ERN (Nakfa)'), ('ETB', 'ETB (Ethiopian Birr)'), ('EUR', 'EUR (Euro)'), ('FJD', 'FJD (Fiji Dollar)'), ('FKP', 'FKP (Falkland Islands Pound)'), ('GBP', 'GBP (Pound Sterling)'), ('GEL', 'GEL (Lari)'), ('GHS', 'GHS (Ghana Cedi)'), ('GIP', 'GIP (Gibraltar Pound)'), ('GMD', 'GMD (Dalasi)'), ('GNF', 'GNF (Guinea Franc)'), ('GTQ', 'GTQ (Quetzal)'), ('GYD', 'GYD (Guyana Dollar)'), ('HKD', 'HKD (Hong Kong Dollar)'), ('HNL', 'HNL (Lempira)'), ('HRK', 'HRK (Kuna)'), ('HTG', 'HTG (Gourde)'), ('HUF', 'HUF (Forint)'), ('IDR', 'IDR (Rupiah)'), ('ILS', 'ILS (New Israeli Sheqel)'), ('INR', 'INR (Indian Rupee)'), ('IQD', 'IQD (Iraqi Dinar)'), ('IRR', 'IRR (Iranian Rial)'), ('ISK', 'ISK (Iceland Krona)'), ('JMD', 'JMD (Jamaican Dollar)'), ('JOD', 'JOD (Jordanian Dinar)'), ('JPY', 'JPY (Yen)'), ('KES', 'KES (Kenyan Shilling)'), ('KGS', 'KGS (Som)'), ('KHR', 'KHR (Riel)'), ('KMF', 'KMF (Comoro Franc)'), ('KPW', 'KPW (North Korean Won)'), ('KRW', 'KRW (Won)'), ('KWD', 'KWD (Kuwaiti Dinar)'), ('KYD', 'KYD (Cayman Islands Dollar)'), ('KZT', 'KZT (Tenge)'), ('LAK', 'LAK (Kip)'), ('LBP', 'LBP (Lebanese Pound)'), ('LKR', 'LKR (Sri Lanka Rupee)'), ('LRD', 'LRD (Liberian Dollar)'), ('LSL', 'LSL (Loti)'), ('LYD', 'LYD (Libyan Dinar)'), ('MAD', 'MAD (Moroccan Dirham)'), ('MDL', 'MDL (Moldovan Leu)'), ('MGA', 'MGA (Malagasy Ariary)'), ('MKD', 'MKD (Denar)'), ('MMK', 'MMK (Kyat)'), ('MNT', 'MNT (Tugrik)'), ('MOP', 'MOP (Pataca)'), ('MRO', 'MRO (Ouguiya)'), ('MUR', 'MUR (Mauritius Rupee)'), ('MVR', 'MVR (Rufiyaa)'), ('MWK', 'MWK (Malawi Kwacha)'), ('MXN', 'MXN (Mexican Peso)'), ('MYR', 'MYR (Malaysian Ringgit)'), ('MZN', 'MZN (Mozambique Metical)'), ('NAD', 'NAD (Namibia Dollar)'), ('NGN', 'NGN (Naira)'), ('NIO', 'NIO (Cordoba Oro)'), ('NOK', 'NOK (Norwegian Krone)'), ('NPR', 'NPR (Nepalese Rupee)'), ('NZD', 'NZD (New Zealand Dollar)'), ('OMR', 'OMR (Rial Omani)'), ('PAB', 'PAB (Balboa)'), ('PEN', 'PEN (Sol)'), ('PGK', 'PGK (Kina)'), ('PHP', 'PHP (Philippine Peso)'), ('PKR', 'PKR (Pakistan Rupee)'), ('PLN', 'PLN (Zloty)'), ('PYG', 'PYG (Guarani)'), ('QAR', 'QAR (Qatari Rial)'), ('RON', 'RON (Romanian Leu)'), ('RSD', 'RSD (Serbian Dinar)'), ('RUB', 'RUB (Russian Ruble)'), ('RWF', 'RWF (Rwanda Franc)'), ('SAR', 'SAR (Saudi Riyal)'), ('SBD', 'SBD (Solomon Islands Dollar)'), ('SCR', 'SCR (Seychelles Rupee)'), ('SDG', 'SDG (Sudanese Pound)'), ('SEK', 'SEK (Swedish Krona)'), ('SGD', 'SGD (Singapore Dollar)'), ('SHP', 'SHP (Saint Helena Pound)'), ('SLL', 'SLL (Leone)'), ('SOS', 'SOS (Somali Shilling)'), ('SRD', 'SRD (Surinam Dollar)'), ('SSP', 'SSP (South Sudanese Pound)'), ('STD', 'STD (Dobra)'), ('SVC', 'SVC (El Salvador Colon)'), ('SYP', 'SYP (Syrian Pound)'), ('SZL', 'SZL (Lilangeni)'), ('THB', 'THB (Baht)'), ('TJS', 'TJS (Somoni)'), ('TMT', 'TMT (Turkmenistan New Manat)'), ('TND', 'TND (Tunisian Dinar)'), ('TOP', 'TOP (Pa\u2019anga)'), ('TRY', 'TRY (Turkish Lira)'), ('TTD', 'TTD (Trinidad and Tobago Dollar)'), ('TWD', 'TWD (New Taiwan Dollar)'), ('TZS', 'TZS (Tanzanian Shilling)'), ('UAH', 'UAH (Hryvnia)'), ('UGX', 'UGX (Uganda Shilling)'), ('USD', 'USD (US Dollar)'), ('UYU', 'UYU (Peso Uruguayo)'), ('UZS', 'UZS (Uzbekistan Sum)'), ('VEF', 'VEF (Bol\xedvar)'), ('VND', 'VND (Dong)'), ('VUV', 'VUV (Vatu)'), ('WST', 'WST (Tala)'), ('XAF', 'XAF (CFA Franc BEAC)'), ('XAG', 'XAG (Silver)'), ('XAU', 'XAU (Gold)'), ('XBA', 'XBA (Bond Markets Unit European Composite Unit (EURCO))'), ('XBB', 'XBB (Bond Markets Unit European Monetary Unit (E.M.U.-6))'), ('XBC', 'XBC (Bond Markets Unit European Unit of Account 9 (E.U.A.-9))'), ('XBD', 'XBD (Bond Markets Unit European Unit of Account 17 (E.U.A.-17))'), ('XCD', 'XCD (East Caribbean Dollar)'), ('XDR', 'XDR (SDR (Special Drawing Right))'), ('XOF', 'XOF (CFA Franc BCEAO)'), ('XPD', 'XPD (Palladium)'), ('XPF', 'XPF (CFP Franc)'), ('XPT', 'XPT (Platinum)'), ('XSU', 'XSU (Sucre)'), ('XTS', 'XTS (Codes specifically reserved for testing purposes)'), ('XUA', 'XUA (ADB Unit of Account)'), ('XXX', 'XXX (The codes assigned for transactions where no currency is involved)'), ('YER', 'YER (Yemeni Rial)'), ('ZAR', 'ZAR (Rand)'), ('ZMW', 'ZMW (Zambian Kwacha)'), ('ZWL', 'ZWL (Zimbabwe Dollar)')], help_text=b'The currency used when making a transaction.', max_length=4)),
                ('transaction_xe_rate', models.DecimalField(blank=True, decimal_places=4, help_text=b'Currency exchange rate from document currency to transaction_currency.', max_digits=16, null=True)),
                ('transaction_xe_date', models.DateField(blank=True, help_text=b'Date of the transaction exchange rate.', null=True)),
                ('state', django_fsm.FSMField(choices=[(b'draft', 'Draft'), (b'issued', 'Issued'), (b'paid', 'Paid'), (b'canceled', 'Canceled')], default=b'draft', help_text=b'The state the invoice is in.', max_length=10, verbose_name=b'State')),
                ('_total', models.DecimalField(blank=True, decimal_places=2, max_digits=19, null=True)),
                ('_total_in_transaction_currency', models.DecimalField(blank=True, decimal_places=2, max_digits=19, null=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='silver.Customer')),
                ('pdf', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='silver.PDF')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='silver.Provider')),
                ('related_document', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='reverse_related_document', to='silver.BillingDocumentBase')),
            ],
            options={
                'ordering': ('-issue_date', 'series', '-number'),
            },
        ),
        migrations.RunPython(move_documents_to_billing_document,
                             migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='invoice',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='pdf',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='proforma',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='provider',
        ),
        migrations.AlterUniqueTogether(
            name='proforma',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='proforma',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='proforma',
            name='invoice',
        ),
        migrations.RemoveField(
            model_name='proforma',
            name='pdf',
        ),
        migrations.RemoveField(
            model_name='proforma',
            name='provider',
        ),
        migrations.AlterField(
            model_name='billinglog',
            name='invoice',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invoice_billing_logs', to='silver.Invoice'),
        ),
        migrations.AlterField(
            model_name='billinglog',
            name='proforma',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='proforma_billing_logs', to='silver.Proforma'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='invoice',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invoice_transactions', to='silver.Invoice'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='proforma',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='proforma_transactions', to='silver.Proforma'),
        ),
        migrations.DeleteModel(
            name='Invoice',
        ),
        migrations.DeleteModel(
            name='Proforma',
        ),
        migrations.AlterUniqueTogether(
            name='billingdocumentbase',
            unique_together=set([('kind', 'provider', 'series', 'number')]),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('silver.billingdocumentbase',),
        ),
        migrations.CreateModel(
            name='Proforma',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('silver.billingdocumentbase',),
        ),
        migrations.RunSQL(
            sql="DROP VIEW IF EXISTS silver_document;",
            reverse_sql=""
        )
    ]
