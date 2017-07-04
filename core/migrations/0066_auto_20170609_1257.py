# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2017-06-09 19:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0065_competition_frame_label_print_1'),
    ]

    operations = [
        migrations.AddField(
            model_name='competition',
            name='long_name',
            field=models.CharField(blank=True, default=b'', max_length=80, verbose_name='Long Name'),
        ),
        migrations.AlterField(
            model_name='participant',
            name='seed_option',
            field=models.SmallIntegerField(choices=[(1, '-'), (0, 'Seed Early'), (2, 'Seed Late'), (3, 'Seed Last')], default=1, verbose_name='Seed Option'),
        ),
    ]