# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0003_v0_5'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='file',
            options={'verbose_name': 'File'},
        ),
        migrations.AddField(
            model_name='file',
            name='accessionid',
            field=models.TextField(help_text=b'Accession ID of originating transfer', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='file',
            name='origin',
            field=django_extensions.db.fields.UUIDField(default='', help_text=b'Unique identifier of originating Archivematica dashboard', max_length=36, editable=False, blank=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='file',
            name='package',
            field=models.ForeignKey(to='locations.Package', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='file',
            name='source_package',
            field=models.TextField(help_text=b'Unique identifier of originating unit', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='event_type',
            field=models.CharField(max_length=8, choices=[(b'DELETE', b'delete'), (b'RECOVER', b'recover')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='location',
            name='purpose',
            field=models.CharField(help_text=b'Purpose of the space.  Eg. AIP storage, Transfer source', max_length=2, choices=[(b'AR', b'AIP Recovery'), (b'AS', b'AIP Storage'), (b'CP', b'Currently Processing'), (b'DS', b'DIP Storage'), (b'SD', b'FEDORA Deposits'), (b'SS', b'Storage Service Internal Processing'), (b'BL', b'Transfer Backlog'), (b'TS', b'Transfer Source')]),
            preserve_default=True,
        ),
    ]
