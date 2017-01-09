# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import silver.models.payment_processors.fields


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0017_auto_20161230_1420'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='payment_processor',
            field=silver.models.payment_processors.fields.PaymentProcessorField(max_length=256),
        ),
    ]
