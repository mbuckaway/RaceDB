# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-12-27 16:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0046_auto_20161223_1028'),
    ]

    operations = [
        migrations.AddField(
            model_name='racetimemassstart',
            name='lap_kmh',
            field=models.FloatField(blank=True, default=0.0, verbose_name='Lap km/h'),
        ),
        migrations.AddField(
            model_name='racetimett',
            name='lap_kmh',
            field=models.FloatField(blank=True, default=0.0, verbose_name='Lap km/h'),
        ),
        migrations.AddField(
            model_name='resultmassstart',
            name='ave_kmh',
            field=models.FloatField(blank=True, default=0.0, null=True, verbose_name='Ave km/h'),
        ),
        migrations.AddField(
            model_name='resulttt',
            name='ave_kmh',
            field=models.FloatField(blank=True, default=0.0, null=True, verbose_name='Ave km/h'),
        ),
        migrations.AddField(
            model_name='wave',
            name='rank_categories_together',
            field=models.BooleanField(default=False, help_text='If False, Categories in the Wave will be ranked seperately.  If True, all Categories in the Wave will be ranked together.', verbose_name='Rank Categories Together'),
        ),
        migrations.AddField(
            model_name='wavett',
            name='rank_categories_together',
            field=models.BooleanField(default=False, help_text='If False, Categories in the Wave will be ranked seperately.  If True, all Categories in the Wave will be ranked together.', verbose_name='Rank Categories Together'),
        ),
    ]
