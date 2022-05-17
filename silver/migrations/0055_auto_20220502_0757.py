# Generated by Django 3.1.12 on 2022-05-12 11:41
from datetime import datetime

from django.db import migrations, models
from django.db.models.functions import TruncTime
from django.utils import timezone


def change_end_date_to_end_of_day(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    MeteredFeatureUnitsLog = apps.get_model('silver', 'MeteredFeatureUnitsLog')

    if MeteredFeatureUnitsLog.objects.annotate(end_time=TruncTime('end_date')).filter(end_time__gt='00:00:00').exists():
        # This check should handle a reapplication of this migration after it's already been applied
        # and reverted (it works when using sqlite, might not be possible to handle on other DBs)
        return

    for mful in MeteredFeatureUnitsLog.objects.using(db_alias):
        if mful.end_date:
            mful.end_date = datetime.combine(
                mful.end_date.date(),
                datetime.max.time(),
                tzinfo=timezone.utc,
            ).replace(microsecond=0)

            mful.save(using=db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ('silver', '0054_auto_20210628_1125'),
    ]

    operations = [
        migrations.AddField(
            model_name='meteredfeatureunitslog',
            name='divider',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.RenameField(
            model_name='meteredfeatureunitslog',
            old_name='divider',
            new_name='annotation',
        ),
        migrations.AlterField(
            model_name='meteredfeatureunitslog',
            name='end_date',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='meteredfeatureunitslog',
            name='start_date',
            field=models.DateTimeField(),
        ),
        migrations.RunPython(
            change_end_date_to_end_of_day,
            migrations.RunPython.noop
        ),
        migrations.RenameField(
            model_name='meteredfeatureunitslog',
            old_name='end_date',
            new_name='end_datetime',
        ),
        migrations.RenameField(
            model_name='meteredfeatureunitslog',
            old_name='start_date',
            new_name='start_datetime',
        ),
        migrations.AlterUniqueTogether(
            name='meteredfeatureunitslog',
            unique_together={('metered_feature', 'subscription', 'start_datetime', 'end_datetime', 'annotation')},
        ),
    ]
